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
    if limit < 1: raise ValueError("limit must be >= 1")
    command = ["llmfit", "recommend", "--json", "--limit", str(limit)]
    if use_case: command.extend(["--use-case", use_case])
    if max_context is not None:
        if max_context < 1: raise ValueError("max_context must be >= 1")
        command.extend(["--max-context", str(max_context)])
    return command

def run_recommend(*, limit: int = 5, use_case: str | None = None, max_context: int | None = None, timeout_seconds: int = 30) -> LLMFitResult:
    command = build_recommend_command(limit=limit, use_case=use_case, max_context=max_context)
    raw = _run_json(command, timeout_seconds=timeout_seconds)
    models = raw.get("models", [])
    if not isinstance(models, list): raise LLMFitError("LLMFit JSON field 'models' must be a list")
    system = raw.get("system", {})
    return LLMFitResult(command=tuple(command), version=raw.get("version") if isinstance(raw.get("version"), str) else None, system=system if isinstance(system, dict) else {}, models=tuple(m for m in models if isinstance(m, dict)), raw=raw)

def run_system(*, timeout_seconds: int = 30) -> Mapping[str, Any]:
    return _run_json(["llmfit", "--json", "system"], timeout_seconds=timeout_seconds)

def normalise_hardware(result: LLMFitResult | Mapping[str, Any]) -> dict[str, Any]:
    """Map current LLMFit facts without inventing dedicated VRAM.

    LLMFit reports integrated Intel/Apple memory as shared or unified memory.
    LEONES therefore preserves the numeric capacity but labels its memory kind
    so downstream selection cannot mistake it for dedicated VRAM.
    """
    root = result.raw if isinstance(result, LLMFitResult) else result
    if not isinstance(root, Mapping):
        root = {}
    source = result.system if isinstance(result, LLMFitResult) else root.get("system", root)
    if not isinstance(source, Mapping):
        source = {}
    node = root.get("node", {}) if isinstance(root.get("node", {}), Mapping) else {}

    gpus = source.get("gpus")
    first = gpus[0] if isinstance(gpus, list) and gpus and isinstance(gpus[0], Mapping) else {}
    gpu = first.get("name") or source.get("gpu_name")
    vram = first.get("vram_gb") if first.get("vram_gb") is not None else source.get("gpu_vram_gb")
    backend = first.get("backend") or source.get("backend")
    unified = bool(first.get("unified_memory", source.get("unified_memory", False)))
    memory_kind = "unified" if unified else ("dedicated" if vram is not None else None)

    cpu = source.get("cpu_name") or source.get("cpu")
    ram = source.get("total_ram_gb") or source.get("ram_gb")
    os_name = node.get("os") or source.get("os") or source.get("os_name")
    architecture = node.get("architecture") or source.get("architecture") or source.get("arch")

    return {
        "source": "llmfit",
        "source_version": result.version if isinstance(result, LLMFitResult) else None,
        "cpu": cpu,
        "ram_gb": ram,
        "gpu": gpu,
        "vram_gb": vram,
        "gpu_memory_kind": memory_kind,
        "unified_memory": unified,
        "os": os_name,
        "architecture": architecture,
        "accelerators": [backend] if backend else [],
        "verification": "detected",
        "raw": dict(source),
    }

def normalise_candidates(result: LLMFitResult) -> list[dict[str, Any]]:
    candidates=[]
    for rank, model in enumerate(result.models, start=1):
        candidates.append({"rank":rank,"source":"llmfit","model":model.get("name") or model.get("id"),"fit":model.get("fit") or model.get("fit_level") or model.get("score"),"estimated_tps":model.get("estimated_tps") or model.get("tps"),"quantization":model.get("quantization") or model.get("quant") or model.get("best_quant"),"raw":dict(model)})
    return candidates
