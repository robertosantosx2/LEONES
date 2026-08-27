#!/usr/bin/env python3
"""FreeToken eligibility contract for LEONES runtime selection.

This module is deliberately a gate, not an executor. It prevents FreeToken from
being selected merely because a model can be made to fit in memory. The decision
requires an MoE workload plus the measured host/GPU/interconnect signals that
FreeToken's design depends on. Actual execution remains behind the trusted
runtime command resolver and the benchmark harness.
"""

from __future__ import annotations

from typing import Any

RUNTIME_NAME = "FreeToken"
RUNTIME_CLASS = "edge-moe-bandwidth-adaptive"
REQUIRED_HARDWARE_SIGNALS = (
    "vram_gb",
    "ram_gb",
    "host_memory_bandwidth_gbps",
    "pcie_h2d_bandwidth_gbps",
    "cpu_moe_bandwidth_gbps",
)


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and value >= 0 else None


def evaluate_freetoken_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return an auditable eligibility decision without inventing measurements."""
    model = candidate.get("model") or {}
    hardware = candidate.get("hardware") or {}
    workload = candidate.get("workload") or {}
    moe = candidate.get("moe") or {}

    reasons: list[str] = []
    missing: list[str] = []
    for signal in REQUIRED_HARDWARE_SIGNALS:
        if _number(hardware.get(signal)) is None:
            missing.append(signal)

    is_moe = bool(moe.get("is_moe"))
    agentic = bool(workload.get("agentic"))
    total_params = _number(model.get("total_params_b"))
    vram = _number(hardware.get("vram_gb"))
    model_weight_gb = _number(model.get("quantized_weight_gb"))

    if not is_moe:
        reasons.append("FreeToken is specialized for MoE workloads")
    if not agentic:
        reasons.append("agentic workload affinity is absent")
    if missing:
        reasons.append("required measured bandwidth signals are missing")
    if total_params is None:
        reasons.append("model.total_params_b is missing")
    if vram is None:
        reasons.append("hardware.vram_gb is missing")
    if model_weight_gb is not None and vram is not None and model_weight_gb <= vram:
        reasons.append(
            "model already fits in GPU memory; FreeToken is not justified by capacity alone"
        )

    eligible = not reasons
    return {
        "runtime": RUNTIME_NAME,
        "runtime_class": RUNTIME_CLASS,
        "eligible": eligible,
        "selection_rule": "moe + agentic + measured host/PCIe/CPU bandwidth + GPU/host memory profile",
        "missing_signals": missing,
        "reasons": reasons,
    }


__all__ = [
    "RUNTIME_NAME",
    "RUNTIME_CLASS",
    "REQUIRED_HARDWARE_SIGNALS",
    "evaluate_freetoken_candidate",
]
