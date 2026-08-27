"""Deterministic preselection of inference configuration before model scoring."""

from __future__ import annotations
from typing import Any

OPTIMIZATION_FAMILIES = {
    "QUANTIZATION",
    "OFFLOAD / STREAMING",
    "SPARSE / MoE",
    "CACHE / DECODING",
    "COMPILED / HARDWARE-SPECIFIC",
    "DISTRIBUTED",
    "EXPERIMENTAL",
}


def resolve_inference_configuration(
    *,
    workload: str,
    hardware: dict[str, Any],
    runtime: str | None = None,
    optimizations: list[str] | None = None,
    is_moe: bool | None = None,
    context_tokens: int = 4096,
) -> dict[str, Any]:
    """Produce a configuration envelope before candidate model ranking.

    Runtime availability and trusted commands are deliberately checked later by
    runtime-selection.v1; this function records the preselection decision only.
    """
    if not isinstance(workload, str) or not workload.strip():
        raise ValueError("use case/workload is required before model evaluation")
    if not isinstance(hardware, dict) or not hardware:
        raise ValueError("hardware profile is required before model evaluation")
    if context_tokens < 1:
        raise ValueError("context_tokens must be positive")
    selected = list(dict.fromkeys(optimizations or []))
    invalid = [x for x in selected if not isinstance(x, str) or not x.strip()]
    if invalid:
        raise ValueError(f"invalid optimization entries: {invalid}")
    return {
        "use_case": workload.strip(),
        "hardware": hardware,
        "runtime": runtime,
        "optimizations": selected,
        "optimization_families": [x for x in selected if x in OPTIMIZATION_FAMILIES],
        "is_moe": is_moe,
        "context_tokens": context_tokens,
        "decision_status": "configuration_preselected",
        "measurement": "not_measured",
    }
