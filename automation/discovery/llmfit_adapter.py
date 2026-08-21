#!/usr/bin/env python3
"""Executable bridge from LLMFit to the LEONES recommendation contract.

LLMFit remains a preselector/estimator. This module preserves its estimates,
adds runtime availability, and exposes deterministic candidate selection. It
never upgrades an estimate to a LEONES measurement.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

FIT_ORDER = {"perfect": 3, "good": 2, "marginal": 1, "too_tight": 0}
RUNTIMES = ["mlx", "llamacpp", "vllm", "airllm"]


@dataclass
class RecommendationCandidate:
    candidate_id: str
    model_id: str
    provider: str | None
    score: float | None
    fit_level: str
    run_mode: str | None
    runtime: str | None
    best_quant: str | None
    estimated_tps: float | None
    measured_tps: float | None
    memory_required_gb: float | None
    memory_available_gb: float | None
    utilization_pct: float | None
    context_length: int | None
    usable_context: int | None
    effective_context_length: int | None
    use_case: str | None
    installed: bool
    runtime_available: bool
    runtime_command: str | None
    ollama_name: str | None
    verify_command: str | None
    source: str = "llmfit"
    source_version: str | None = None
    evidence_status: str = "estimated"
    estimate_basis: dict[str, Any] | str | None = None
    notes: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)


def _first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _run(args: list[str]) -> str:
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def _python_import(module: str) -> bool:
    python = shutil.which("python") or shutil.which("python3")
    if not python:
        return False
    try:
        subprocess.run([python, "-c", f"import {module}"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def runtime_command(runtime: str | None) -> str | None:
    if runtime == "llamacpp":
        for name in ("llama-server", "llama-cli", "llama-bench"):
            if shutil.which(name):
                return name
    elif runtime == "mlx":
        for name in ("mlx_lm.server", "mlx_lm.generate"):
            if shutil.which(name):
                return name
        if _python_import("mlx_lm"):
            return "python:mlx_lm"
    elif runtime == "vllm":
        if shutil.which("vllm"):
            return "vllm"
        if _python_import("vllm"):
            return "python:vllm"
    elif runtime == "airllm":
        if _python_import("airllm") and _python_import("torch"):
            return "python:airllm"
    return None


def normalize_candidate(raw: dict[str, Any], *, observed_at: str | None = None,
                        source_version: str | None = None) -> dict[str, Any]:
    """Normalize current and legacy LLMFit fields into stable LEONES fields."""
    model_id = _first(raw, "name", "model", "model_id", "id")
    runtime = raw.get("runtime")
    command = runtime_command(runtime)
    candidate = RecommendationCandidate(
        candidate_id=f"llmfit:{model_id}:{_first(raw, 'best_quant', 'quantization', 'quant') or 'default'}",
        model_id=model_id,
        provider=raw.get("provider"),
        score=_first(raw, "score", "quality_score", "quality"),
        fit_level=str(_first(raw, "fit_level", "fit") or "unknown").lower().replace(" ", "_"),
        run_mode=_first(raw, "run_mode", "mode"),
        runtime=runtime,
        best_quant=_first(raw, "best_quant", "quantization", "quant"),
        estimated_tps=_first(raw, "estimated_tps", "tok_s", "tps", "tokens_per_second"),
        measured_tps=None,
        memory_required_gb=_first(raw, "memory_required_gb", "memory_gb", "mem_gb"),
        memory_available_gb=_first(raw, "memory_available_gb"),
        utilization_pct=raw.get("utilization_pct"),
        context_length=_first(raw, "context_length", "context", "ctx"),
        usable_context=raw.get("usable_context"),
        effective_context_length=raw.get("effective_context_length"),
        use_case=raw.get("use_case"),
        installed=bool(raw.get("installed", False)),
        runtime_available=command is not None,
        runtime_command=command,
        ollama_name=raw.get("ollama_name"),
        verify_command=raw.get("verify_command"),
        source_version=source_version,
        estimate_basis=raw.get("estimate_basis", "llmfit-estimate"),
        notes=list(raw.get("notes") or []),
        raw=raw,
    )
    return asdict(candidate)


def normalize(payload: Any, *, observed_at: str | None = None,
              source_version: str | None = None) -> dict[str, Any]:
    """Normalize LLMFit JSON and preserve its hardware envelope."""
    if isinstance(payload, list):
        candidates, system = payload, None
    elif isinstance(payload, dict):
        system = payload.get("system") or payload.get("hardware")
        candidates = None
        for key in ("models", "recommendations", "results", "data"):
            if key not in payload:
                continue
            value = payload[key]
            if isinstance(value, list):
                candidates = value
                break
            if isinstance(value, dict) and isinstance(value.get("models"), list):
                candidates = value["models"]
                break
            raise ValueError(f"LLMFit collection '{key}' is not a model list")
        if candidates is None:
            raise ValueError("Could not locate a model list in LLMFit JSON")
    else:
        raise TypeError("LLMFit JSON must be an object or list")
    observed_at = observed_at or datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "leones.recommendation-candidates.v1",
        "source": "llmfit",
        "source_version": source_version,
        "observed_at": observed_at,
        "hardware": system,
        "candidates": [normalize_candidate(item, observed_at=observed_at, source_version=source_version)
                       for item in candidates if isinstance(item, dict)],
    }


def llmfit_version() -> str | None:
    binary = shutil.which("llmfit")
    if not binary:
        return None
    try:
        return _run([binary, "--version"]).strip() or None
    except RuntimeError:
        return None


def run_llmfit(args: list[str]) -> dict[str, Any]:
    binary = shutil.which("llmfit")
    if not binary:
        raise FileNotFoundError("llmfit is not installed or not in PATH")
    command = [binary, *args]
    if "--json" not in command:
        command.append("--json")
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return normalize(json.loads(completed.stdout), source_version=llmfit_version())


def recommend(*, use_case: str | None = None, limit: int = 5,
              min_fit: str = "good", max_context: int | None = None,
              force_runtime: str | None = None) -> dict[str, Any]:
    args = ["recommend", "--limit", str(limit), "--min-fit", min_fit]
    if use_case:
        args += ["--use-case", use_case]
    if max_context:
        args = ["--max-context", str(max_context), *args]
    if force_runtime:
        args += ["--force-runtime", force_runtime]
    return run_llmfit(args)


def select_candidate(envelope: dict[str, Any], *, target_tps: float = 10.0,
                     require_installed: bool = False, require_runtime: bool = True) -> dict[str, Any] | None:
    eligible = []
    for row in envelope.get("candidates", []):
        if FIT_ORDER.get(row.get("fit_level"), -1) < FIT_ORDER["good"]:
            continue
        if require_installed and not row.get("installed"):
            continue
        if require_runtime and not row.get("runtime_available"):
            continue
        eligible.append(row)
    if not eligible:
        return None
    def key(row: dict[str, Any]) -> tuple[int, int, float, float]:
        tps = float(row.get("estimated_tps") or 0)
        return (int(tps >= target_tps), FIT_ORDER.get(row.get("fit_level"), -1),
                float(row.get("score") or 0), tps)
    return max(eligible, key=key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input")
    parser.add_argument("--use-case", choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-fit", choices=["perfect", "good", "marginal"], default="good")
    parser.add_argument("--max-context", type=int)
    parser.add_argument("--force-runtime", choices=RUNTIMES)
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--target-tps", type=float, default=10.0)
    parser.add_argument("--require-installed", action="store_true")
    ns = parser.parse_args()
    if ns.input:
        with open(ns.input, encoding="utf-8") as fh:
            result = normalize(json.load(fh))
    else:
        result = recommend(use_case=ns.use_case, limit=ns.limit, min_fit=ns.min_fit,
                           max_context=ns.max_context, force_runtime=ns.force_runtime)
    if ns.select:
        result["selected"] = select_candidate(result, target_tps=ns.target_tps,
                                               require_installed=ns.require_installed)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
