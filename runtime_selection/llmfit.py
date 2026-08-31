"""LLMFit integration boundary for RC2 hardware intelligence.

This module deliberately does not implement model-fit heuristics. It consumes
LLMFit's machine-readable output and normalises the result for LEONES.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import subprocess
from typing import Any, Mapping, Sequence


class LLMFitError(RuntimeError):
    """Raised when LLMFit is unavailable or returns invalid output."""


@dataclass(frozen=True)
class LLMFitResult:
    command: tuple[str, ...]
    version: str | None
    system: Mapping[str, Any]
    models: Sequence[Mapping[str, Any]]
    raw: Mapping[str, Any]


def executable() -> str | None:
    return shutil.which("llmfit")


def _run_json(command: list[str], *, timeout_seconds: int = 30) -> Mapping[str, Any]:
    if executable() is None:
        raise LLMFitError("llmfit executable not found")
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=timeout_seconds)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LLMFitError(f"LLMFit execution failed: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LLMFitError(f"LLMFit exited with {completed.returncode}: {detail}")
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LLMFitError("LLMFit did not return valid JSON") from exc
    if not isinstance(raw, dict):
        raise LLMFitError("LLMFit JSON root must be an object")
    return raw


def build_recommend_command(*, limit: int = 5, use_case: str | None = None, max_context: int | None = None) -> list[str]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    command = ["llmfit", "recommend", "--json", "--limit", str(limit)]
    if use_case:
        command.extend(["--use-case", use_case])
    if max_context is not None:
        if max_context < 1:
            raise ValueError("max_context must be >= 1")
        command.extend(["--max-context", str(max_context)])
    return command


def run_recommend(*, limit: int = 5, use_case: str | None = None, max_context: int | None = None, timeout_seconds: int = 30) -> LLMFitResult:
    command = build_recommend_command(limit=limit, use_case=use_case, max_context=max_context)
    raw = _run_json(command, timeout_seconds=timeout_seconds)
    models = raw.get("models", [])
    if not isinstance(models, list):
        raise LLMFitError("LLMFit JSON field 'models' must be a list")
    system = raw.get("system", {})
    return LLMFitResult(
        command=tuple(command),
        version=raw.get("version") if isinstance(raw.get("version"), str) else None,
        system=system if isinstance(system, dict) else {},
        models=tuple(m for m in models if isinstance(m, dict)),
        raw=raw,
    )


def run_system(*, timeout_seconds: int = 30) -> Mapping[str, Any]:
    """Read LLMFit's authoritative detected-system JSON."""
    return _run_json(["llmfit", "--json", "system"], timeout_seconds=timeout_seconds)


def normalise_hardware(result: LLMFitResult | Mapping[str, Any]) -> dict[str, Any]:
    """Map current LLMFit system JSON to LEONES canonical hardware fields."""
    source = result.system if isinstance(result, LLMFitResult) else result.get("system", result)
    if not isinstance(source, Mapping):
        source = {}
    gpus = source.get("gpus")
    gpu = None
    vram = None
    backend = None
    if isinstance(gpus, list) and gpus:
        first = gpus[0] if isinstance(gpus[0], Mapping) else {}
        gpu = first.get("name")
        vram = first.get("vram_gb")
        backend = first.get("backend")
    cpu = source.get("cpu") or source.get("cpu_name")
    ram = source.get("ram_gb") or source.get("total_ram_gb")
    return {
        "source": "llmfit",
        "source_version": result.version if isinstance(result, LLMFitResult) else None,
        "cpu": cpu,
        "ram_gb": ram,
        "gpu": gpu or ("Integrated GPU" if source.get("has_gpu") else None),
        "vram_gb": vram,
        "os": source.get("os"),
        "architecture": source.get("architecture"),
        "accelerators": [backend] if backend else [],
        "verification": "detected",
        "raw": dict(source),
    }


def normalise_candidates(result: LLMFitResult) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for rank, model in enumerate(result.models, start=1):
        candidates.append({
            "rank": rank,
            "source": "llmfit",
            "model": model.get("name") or model.get("id"),
            "fit": model.get("fit") or model.get("fit_level") or model.get("score"),
            "estimated_tps": model.get("estimated_tps") or model.get("tps"),
            "quantization": model.get("quantization") or model.get("quant") or model.get("best_quant"),
            "raw": dict(model),
        })
    return candidates
