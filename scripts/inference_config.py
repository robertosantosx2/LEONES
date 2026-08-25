"""Deterministic preselection of inference configuration before model scoring."""
from __future__ import annotations
from typing import Any

OPTIMIZATION_FAMILIES = {
    "QUANTIZATION", "OFFLOAD / STREAMING", "SPARSE / MoE", "CACHE / DECODING",
    "COMPILED / HARDWARE-SPECIFIC", "DISTRIBUTED", "EXPERIMENTAL"
}


def resolve_inference_configuration(*, workload: str, hardware: dict[str, Any],
                                    runtime: str | None = None,
                                    optimizations: list[str] | None = None,
                                    is_moe: bool | None = None,
                                    context_tokens: int = 4096) -> dict[str, Any]:
    """Produce a configuration envelope before candidate model ranking.

    This does not claim that a runtime is executable. Runtime availability and
    trusted commands are checked later by runtime-selection.v1.
    """
    if not workload or not workload.strip():
        raise ValueError("use case/workload is required before model evaluation")
    if not hardware:
        raise ValueError("hardware profile is required before model evaluation")
    if context_tokens < 1:
        raise ValueError("context_tokens must be positive")
    selected = list(dict.fromkeys(optimizations or []))
    unknown = [x for x in selected if x not in OPTIMIZATION_FAMILIES and not isinstance(x, str)]
    if unknown:
        raise ValueError(f"invalid optimization entries: {unknown}")
    return {
        "use_case": workload,
        "hardware": hardware,
        "runtime": runtime,
        "optimizations": selected,
        "is_moe": is_moe,
        "context_tokens": context_tokens,
        "decision_status": "configuration_preselected",
        "measurement": "not_measured",
    }
