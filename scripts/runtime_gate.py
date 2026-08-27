#!/usr/bin/env python3
"""Canonical selector -> runtime-selection.v1 gate for V1.1 runtimes."""
from __future__ import annotations
from typing import Any
from scripts.runtime_registry import get_runtime
from scripts.runtimes.v1_1_adapters import get_adapter
ALLOWED_FOR_EXECUTION = {"TOP_N", "BENCHMARK_REQUIRED"}
SCHEMA_VERSION = "1.0"

def resolve_runtime(candidate: dict[str, Any], *, available_runtimes: set[str] | None = None,
                    runtime_commands: dict[str, list[str]] | None = None, hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    status = str(candidate.get("selection_status") or "")
    if status not in ALLOWED_FOR_EXECUTION:
        raise ValueError(f"candidate is not executable from selection state: {status or 'missing'}")
    model_id = candidate.get("model_id") or candidate.get("model_name")
    model_name = candidate.get("model_name") or model_id
    runtime_name = candidate.get("runtime")
    quantization = candidate.get("quantization")
    if not model_id:
        raise ValueError("selected candidate has no model identity")
    if not runtime_name:
        raise ValueError("selected candidate has no runtime")
    if not quantization:
        raise ValueError("selected candidate has no quantization")
    if candidate.get("optimization_families") is None:
        raise ValueError("optimization plan is missing")
    if available_runtimes is not None and runtime_name not in available_runtimes:
        raise ValueError(f"runtime is unavailable: {runtime_name}")
    entry = get_runtime(runtime_name)
    adapter = get_adapter(entry.id)
    trusted_override = (runtime_commands or {}).get(runtime_name)
    if trusted_override is not None and (not trusted_override or not all(isinstance(x, str) for x in trusted_override)):
        raise ValueError(f"invalid trusted command for runtime: {runtime_name}")
    entrypoint = trusted_override if trusted_override is not None else list(entry.entrypoint["argv"])
    # Authorization comes from the trusted registry/adapter binding, not from whether
    # the command happens to have argv tokens. This permits adapter-controlled runtimes.
    execution_authorized = bool(entry.entrypoint.get("kind")) and adapter.adapter_id == entry.adapter
    hw = dict(hardware or {})
    hw.update(candidate.get("hardware") or {})
    model = candidate.get("model") or {}
    runtime_plan = {"schema_version": SCHEMA_VERSION, "model_id": model_id, "model": model,
        "runtime": {"name": entry.id, "version": candidate.get("runtime_version")}, "quantization": quantization,
        "model_format": candidate.get("model_format"), "architecture_class": "moe" if (candidate.get("moe") or {}).get("is_moe") else "dense",
        "execution_mode": candidate.get("execution_mode"), "backend": candidate.get("backend"), "required_capabilities": candidate.get("required_capabilities") or [],
        "hardware": hw, "workload": candidate.get("workload") or {}, "moe": candidate.get("moe") or {}, "execution_authorized": execution_authorized}
    spec = adapter.prepare(runtime_plan, entry)
    llmfit = candidate.get("llmfit") or {}
    plan = {"schema_version": SCHEMA_VERSION, "category": candidate.get("category"), "architecture_class": runtime_plan["architecture_class"],
        "parameters": {"total_parameters_m": model.get("total_params_m"), "active_parameters_m": model.get("active_params_m"), "selection_basis": candidate.get("parameter_selection_basis")},
        "model_id": model_id, "model": {"id": model_id, "name": model_name, "revision": candidate.get("revision")}, "variant": candidate.get("variant"),
        "runtime": {"name": entry.id, "adapter": adapter.adapter_id, "entrypoint": entrypoint, "entrypoint_kind": entry.entrypoint["kind"], "version": candidate.get("runtime_version")},
        "optimization_families": candidate.get("optimization_families") or [], "quantization": quantization,
        "hardware": {"ram_gb": hw.get("ram_gb", candidate.get("memory_available_gb") or 0), "os": hw.get("os", "unknown"), "cpu": hw.get("cpu"), "gpu": hw.get("gpu"), "vram_gb": hw.get("vram_gb"),
                     "host_memory_bandwidth_gbps": hw.get("host_memory_bandwidth_gbps"), "pcie_h2d_bandwidth_gbps": hw.get("pcie_h2d_bandwidth_gbps"), "cpu_moe_bandwidth_gbps": hw.get("cpu_moe_bandwidth_gbps")},
        "workload": candidate.get("workload") or {}, "selection_status": status, "selection_rank": candidate.get("rank"), "fit_score": candidate.get("fit_score"),
        "evidence_level": candidate.get("evidence_level"), "execution_authorized": execution_authorized, "measurement_required": True,
        "benchmark_probe": status == "BENCHMARK_REQUIRED", "estimated_tps": llmfit.get("estimated_tps"), "measured_tps": None}
    plan.update({key: value for key, value in spec.metadata.items() if key == "runtime_eligibility"})
    return plan

def gate_selection(selection: dict[str, Any], *, available_runtimes: set[str] | None = None,
                   runtime_commands: dict[str, list[str]] | None = None, hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    plans, blocked = [], []
    for candidate in selection.get("candidates", []):
        try:
            plans.append(resolve_runtime(candidate, available_runtimes=available_runtimes, runtime_commands=runtime_commands, hardware=hardware))
        except ValueError as exc:
            blocked.append({"model_id": candidate.get("model_id") or candidate.get("model_name"), "selection_status": candidate.get("selection_status"), "reason": str(exc)})
    return {"schema_version": SCHEMA_VERSION, "gate": "LEONES-runtime-selection-gate", "execution_plans": plans, "blocked": blocked,
            "counts": {"plans": len(plans), "blocked": len(blocked)}}
