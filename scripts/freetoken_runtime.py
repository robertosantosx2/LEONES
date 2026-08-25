#!/usr/bin/env python3
"""FreeToken eligibility contract for LEONES runtime selection."""
from __future__ import annotations
from typing import Any

RUNTIME_NAME = "FreeToken"
RUNTIME_CLASS = "edge-moe-bandwidth-adaptive"
REQUIRED_HARDWARE_SIGNALS = ("vram_gb", "ram_gb", "host_memory_bandwidth_gbps", "pcie_h2d_bandwidth_gbps", "cpu_moe_bandwidth_gbps")

def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value >= 0 else None

def evaluate_freetoken_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    model = candidate.get("model") or {}
    hardware = candidate.get("hardware") or {}
    workload = candidate.get("workload") or {}
    moe = candidate.get("moe") or {}
    reasons: list[str] = []
    missing: list[str] = []
    for signal in REQUIRED_HARDWARE_SIGNALS:
        if _number(hardware.get(signal)) is None: missing.append(signal)
    if not bool(moe.get("is_moe")): reasons.append("FreeToken is specialized for MoE workloads")
    if not bool(workload.get("agentic")): reasons.append("agentic workload affinity is absent")
    if missing: reasons.append("required measured bandwidth signals are missing: " + ", ".join(missing))
    total_params = _number(model.get("total_params_b"))
    vram = _number(hardware.get("vram_gb"))
    model_weight_gb = _number(model.get("quantized_weight_gb"))
    if total_params is None: reasons.append("model.total_params_b is missing")
    if vram is None: reasons.append("hardware.vram_gb is missing")
    if model_weight_gb is not None and vram is not None and model_weight_gb <= vram:
        reasons.append("model already fits in GPU memory; FreeToken is not justified by capacity alone")
    return {"runtime": RUNTIME_NAME, "runtime_class": RUNTIME_CLASS, "eligible": not reasons,
            "selection_rule": "moe + agentic + measured host/PCIe/CPU bandwidth + GPU/host memory profile",
            "missing_signals": missing, "reasons": reasons}

__all__ = ["RUNTIME_NAME", "RUNTIME_CLASS", "REQUIRED_HARDWARE_SIGNALS", "evaluate_freetoken_candidate"]
