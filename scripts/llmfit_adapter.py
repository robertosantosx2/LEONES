#!/usr/bin/env python3
"""Bridge llmfit output into the LEONES recommendation contract.

llmfit is an estimator/preselector. This adapter deliberately preserves its
provenance and never upgrades an estimate to a LEONES measurement.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

FIT_ORDER = {"perfect": 3, "good": 2, "marginal": 1, "too_tight": 0}


@dataclass
class RecommendationCandidate:
    candidate_id: str
    model: str
    provider: str | None
    score: float | None
    fit_level: str
    run_mode: str | None
    runtime: str | None
    best_quant: str | None
    estimated_tps: float | None
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
    notes: list[str] = field(default_factory=list)


def _run(args: list[str]) -> str:
    proc = subprocess.run(args, check=False, capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"command failed ({proc.returncode}): {' '.join(args)}\n{proc.stderr.strip()}")
    return proc.stdout


def llmfit_json(*args: str) -> dict[str, Any]:
    """Run llmfit and parse its machine-readable JSON envelope."""
    output = _run(["llmfit", *args, "--json"])
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError("llmfit did not return valid JSON") from exc


def llmfit_version() -> str | None:
    if not shutil.which("llmfit"):
        return None
    try:
        text = _run(["llmfit", "--version"]).strip()
        return text or None
    except RuntimeError:
        return None


def runtime_command(runtime: str | None) -> str | None:
    if runtime == "llamacpp":
        for name in ("llama-server", "llama-cli", "llama-bench"):
            if shutil.which(name):
                return name
    elif runtime == "mlx":
        for name in ("mlx_lm.server", "mlx_lm.generate"):
            if shutil.which(name):
                return name
        if shutil.which("python"):
            try:
                subprocess.run(["python", "-c", "import mlx_lm"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "python:mlx_lm"
            except (OSError, subprocess.SubprocessError):
                pass
    elif runtime == "vllm":
        if shutil.which("vllm"):
            return "vllm"
        if shutil.which("python"):
            try:
                subprocess.run(["python", "-c", "import vllm"], check=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return "python:vllm"
            except (OSError, subprocess.SubprocessError):
                pass
    return None


def _normalise_fit(value: Any) -> str:
    return str(value or "unknown").strip().lower().replace(" ", "_")


def _candidate(raw: dict[str, Any], source_version: str | None) -> RecommendationCandidate:
    model = str(raw.get("name") or raw.get("model") or "")
    runtime = raw.get("runtime")
    return RecommendationCandidate(
        candidate_id=f"llmfit:{model}:{raw.get('best_quant') or 'default'}",
        model=model,
        provider=raw.get("provider"),
        score=raw.get("score"),
        fit_level=_normalise_fit(raw.get("fit_level")),
        run_mode=raw.get("run_mode"),
        runtime=runtime,
        best_quant=raw.get("best_quant"),
        estimated_tps=raw.get("estimated_tps"),
        memory_required_gb=raw.get("memory_required_gb"),
        memory_available_gb=raw.get("memory_available_gb"),
        utilization_pct=raw.get("utilization_pct"),
        context_length=raw.get("context_length"),
        usable_context=raw.get("usable_context"),
        effective_context_length=raw.get("effective_context_length"),
        use_case=raw.get("use_case"),
        installed=bool(raw.get("installed", False)),
        runtime_available=runtime_command(runtime) is not None,
        runtime_command=runtime_command(runtime),
        ollama_name=raw.get("ollama_name"),
        verify_command=raw.get("verify_command"),
        source_version=source_version,
        notes=list(raw.get("notes") or []),
    )


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
    envelope = llmfit_json(*args)
    version = llmfit_version()
    rows = envelope.get("models", [])
    candidates = [_candidate(row, version) for row in rows]
    return {
        "schema_version": "leones.recommendation-candidates.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {"name": "llmfit", "version": version, "evidence_status": "estimated"},
        "request": {"use_case": use_case, "limit": limit, "min_fit": min_fit,
                    "max_context": max_context, "force_runtime": force_runtime},
        "candidates": [asdict(c) for c in candidates],
    }


def select_candidate(envelope: dict[str, Any], *, target_tps: float = 10.0,
                     require_installed: bool = False,
                     require_runtime: bool = True) -> dict[str, Any] | None:
    candidates = envelope.get("candidates", [])
    eligible = []
    for row in candidates:
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
        estimated = float(row.get("estimated_tps") or 0)
        meets = int(estimated >= target_tps)
        return (meets, FIT_ORDER.get(row.get("fit_level"), -1),
                float(row.get("score") or 0), estimated)

    return max(eligible, key=key)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--use-case", choices=["general", "coding", "reasoning", "chat", "multimodal", "embedding"])
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--min-fit", choices=["perfect", "good", "marginal"], default="good")
    parser.add_argument("--max-context", type=int)
    parser.add_argument("--force-runtime", choices=["mlx", "llamacpp", "vllm"])
    parser.add_argument("--select", action="store_true")
    parser.add_argument("--target-tps", type=float, default=10.0)
    parser.add_argument("--require-installed", action="store_true")
    args = parser.parse_args()
    if not shutil.which("llmfit"):
        print("llmfit executable not found", file=sys.stderr)
        return 2
    result = recommend(use_case=args.use_case, limit=args.limit, min_fit=args.min_fit,
                       max_context=args.max_context, force_runtime=args.force_runtime)
    if args.select:
        result["selected"] = select_candidate(result, target_tps=args.target_tps,
                                               require_installed=args.require_installed)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
