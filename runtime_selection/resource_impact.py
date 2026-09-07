"""Resource footprint evaluation for RC4 model installation and runtime.

This module deliberately separates facts from estimates. Every recommendation
gets a resource profile, even when some values are unknown. Unknown is never
silently converted into zero.
"""
from __future__ import annotations

from typing import Any, Mapping

BYTES_PER_GIB = 1024 ** 3
INSTALL_OVERHEAD = 1.10
RUNTIME_MARGIN = 1.20


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _round(value: float | None) -> float | None:
    return round(value, 3) if value is not None else None


def _gib_from_bytes(value: Any) -> float | None:
    number = _number(value)
    return number / BYTES_PER_GIB if number is not None else None


def _weight_memory(parameters_b: Any, bits_per_weight: Any) -> float | None:
    parameters = _number(parameters_b)
    bits = _number(bits_per_weight)
    if parameters is None or bits is None or bits <= 0:
        return None
    return parameters * 1_000_000_000 * bits / 8 / BYTES_PER_GIB


def evaluate_resource_impact(
    *,
    model_evidence: Mapping[str, Any],
    hardware: Mapping[str, Any],
    fit: Mapping[str, Any] | None = None,
    context_tokens: int | None = None,
) -> dict[str, Any]:
    """Return the mandatory resource profile for an installable model.

    ``storage`` prefers an observed Hugging Face repository size. If it is not
    available, it falls back to a clearly-labelled weight-size estimate.
    Runtime memory is likewise an estimate unless a future runtime benchmark
    supplies a measured value. CPU/GPU utilization is not fabricated.
    """
    hf = model_evidence.get("hf") if isinstance(model_evidence.get("hf"), Mapping) else {}
    parameters_b = _number(hf.get("parameters_b"))
    bits = _number((fit or {}).get("bits_per_weight"))
    if bits is None:
        bits = _number((fit or {}).get("bits"))

    observed_bytes = _number(hf.get("used_storage_bytes"))
    observed_gib = _gib_from_bytes(observed_bytes)
    weight_gib = _weight_memory(parameters_b, bits)

    if observed_gib is not None:
        install_artifact_gib = observed_gib
        storage_basis = "huggingface_used_storage"
        storage_confidence = "observed"
    elif weight_gib is not None:
        install_artifact_gib = weight_gib
        storage_basis = "estimated_weight_size"
        storage_confidence = "estimated"
    else:
        install_artifact_gib = None
        storage_basis = "unknown"
        storage_confidence = "unknown"

    disk_required = install_artifact_gib * INSTALL_OVERHEAD if install_artifact_gib is not None else None
    runtime_weight = weight_gib or install_artifact_gib
    runtime_memory = runtime_weight * RUNTIME_MARGIN if runtime_weight is not None else None

    ram_available = _number(hardware.get("ram_gb"))
    vram_available = _number(hardware.get("vram_gb"))
    gpu_memory_required = runtime_memory if vram_available is not None else None
    cpu_memory_required = runtime_memory

    def fit_status(required: float | None, available: float | None) -> str:
        if required is None or available is None:
            return "unknown"
        return "fits" if required <= available else "exceeds"

    return {
        "schema": "leones.rc4.resource-impact.v1",
        "always_present": True,
        "install": {
            "artifact_size_gb": _round(install_artifact_gib),
            "disk_space_required_gb": _round(disk_required),
            "temporary_overhead_factor": INSTALL_OVERHEAD,
            "basis": storage_basis,
            "confidence": storage_confidence,
        },
        "runtime": {
            "weights_memory_gb": _round(weight_gib),
            "estimated_peak_memory_gb": _round(runtime_memory),
            "estimated_ram_required_gb": _round(cpu_memory_required),
            "estimated_vram_required_gb": _round(gpu_memory_required),
            "context_tokens": context_tokens,
            "margin_factor": RUNTIME_MARGIN,
            "confidence": "estimated" if runtime_memory is not None else "unknown",
            "measured": False,
        },
        "hardware_capacity": {
            "ram_available_gb": _round(ram_available),
            "vram_available_gb": _round(vram_available),
            "cpu_memory_status": fit_status(cpu_memory_required, ram_available),
            "gpu_memory_status": fit_status(gpu_memory_required, vram_available),
        },
        "consumption": {
            "cpu_utilization_percent": None,
            "gpu_utilization_percent": None,
            "power_watts": None,
            "reason_unknown": "No local execution measurement has been performed.",
        },
        "decision": (
            "installable_estimate"
            if disk_required is not None and runtime_memory is not None
            else "resource_data_incomplete"
        ),
    }
