#!/usr/bin/env python3
"""Canonical LEONES gate from model selection to runtime-selection.v1.

The gate normalizes selector candidates into a stable runtime-selection contract.
It never invents an executable command: a runtime command must be supplied by a
trusted runtime resolver/configuration before an A01 execution is authorized.
"""
from __future__ import annotations

from typing import Any

ALLOWED_FOR_EXECUTION = {"TOP_N", "BENCHMARK_REQUIRED"}
SCHEMA_VERSION = "1.0"


def resolve_runtime(candidate: dict[str, Any], *, available_runtimes: set[str] | None = None,
                    runtime_commands: dict[str, list[str]] | None = None,
                    hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    status = str(candidate.get("selection_status") or "")
    if status not in ALLOWED_FOR_EXECUTION:
        raise ValueError(f"candidate is not executable from selection state: {status or 'missing'}")
    model_id = candidate.get("model_id") or candidate.get("model_name")
    model_name = candidate.get("model_name") or model_id
    runtime_name = candidate.get("runtime")
    quantization = candidate.get("quantization")
    if not model_id: raise ValueError("selected candidate has no model identity")
    if not runtime_name: raise ValueError("selected candidate has no runtime")
    if not quantization: raise ValueError("selected candidate has no quantization")
    if available_runtimes is not None and runtime_name not in available_runtimes:
        raise ValueError(f"runtime is unavailable: {runtime_name}")
    command = (runtime_commands or {}).get(runtime_name)
    if command is not None and (not command or not all(isinstance(x, str) for x in command)):
        raise ValueError(f"invalid trusted command for runtime: {runtime_name}")
    hw = hardware or {}
    llmfit = candidate.get("llmfit") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": model_id,
        "model": {"id": model_id, "name": model_name, "revision": candidate.get("revision")},
        "variant": candidate.get("variant"),
        "runtime": {"name": runtime_name, "command": command, "version": candidate.get("runtime_version")},
        "quantization": quantization,
        "hardware": {"ram_gb": hw.get("ram_gb", candidate.get("memory_available_gb") or 0), "os": hw.get("os", "unknown"), "cpu": hw.get("cpu"), "gpu": hw.get("gpu"), "vram_gb": hw.get("vram_gb")},
        "selection_status": status,
        "selection_rank": candidate.get("rank"),
        "fit_score": candidate.get("fit_score"),
        "evidence_level": candidate.get("evidence_level"),
        "execution_authorized": command is not None,
        "measurement_required": True,
        "benchmark_probe": status == "BENCHMARK_REQUIRED",
        "estimated_tps": llmfit.get("estimated_tps"),
        "measured_tps": None,
    }


def gate_selection(selection: dict[str, Any], *, available_runtimes: set[str] | None = None,
                   runtime_commands: dict[str, list[str]] | None = None,
                   hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    """Convert selector output into runtime-selection.v1 plans."""
    plans: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for candidate in selection.get("candidates", []):
        try:
            plans.append(resolve_runtime(candidate, available_runtimes=available_runtimes,
                                         runtime_commands=runtime_commands, hardware=hardware))
        except ValueError as exc:
            blocked.append({"model_id": candidate.get("model_id") or candidate.get("model_name"), "selection_status": candidate.get("selection_status"), "reason": str(exc)})
    return {"schema_version": SCHEMA_VERSION, "gate": "LEONES-runtime-selection-gate", "execution_plans": plans, "blocked": blocked, "counts": {"plans": len(plans), "blocked": len(blocked)}}
