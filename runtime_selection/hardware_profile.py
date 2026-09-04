"""RC3 hardware profile normalization and reconciliation.

The physical source is authoritative LEONES host discovery. Hermes may provide
model/runtime fit information, but RC3 does not assume that its public CLI
exposes a stable machine-readable hardware profile. External/declarative data
remains provenance-tagged and never becomes a measurement.
"""
from __future__ import annotations

from typing import Any

UNKNOWN = None


def normalize_hardware(source: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical hardware profile without fabricating values.

    Accepts both the compact legacy shape (``ram_gb``, ``gpu``) and the RC3
    discovery shape (nested ``ram`` and a GPU list).
    """
    ram = source.get("ram") or {}
    ram_gb = source.get("ram_gb", ram.get("total_gb", UNKNOWN))
    gpu = source.get("gpu", UNKNOWN)
    vram_gb = source.get("vram_gb", UNKNOWN)
    if isinstance(gpu, list) and len(gpu) == 1:
        gpu = gpu[0]

    return {
        "schema": source.get("schema", "hardware-profile.v1"),
        "cpu": source.get("cpu", UNKNOWN),
        "ram_gb": ram_gb,
        "ram_available_gb": source.get("ram_available_gb", ram.get("available_gb", UNKNOWN)),
        "gpu": gpu,
        "vram_gb": vram_gb,
        "os": source.get("os", UNKNOWN),
        "architecture": source.get("architecture", UNKNOWN),
        "accelerators": source.get("accelerators", []),
        "backend": source.get("backend", []),
        "source": source.get("source", "unknown"),
        "source_version": source.get("source_version", UNKNOWN),
        "verification": source.get("verification", "declared"),
        "discovery_timestamp": source.get("discovery_timestamp"),
        "memory_modules": source.get("memory_modules", []),
        "vendor_probe": source.get("vendor_probe"),
        "hermes": source.get("hermes"),
    }


def normalize_candidates(raw: list[dict[str, Any]], *, source: str = "external") -> list[dict[str, Any]]:
    """Normalize candidates while retaining ranking/evidence provenance."""
    result = []
    for rank, item in enumerate(raw, 1):
        result.append({
            "model_id": item.get("model_id") or item.get("id"),
            "name": item.get("name") or item.get("model_id") or item.get("id"),
            "rank": item.get("rank", rank),
            "fit": item.get("fit"),
            "estimated_tps": item.get("estimated_tps"),
            "source": item.get("source", source),
            "source_version": item.get("source_version"),
            "evidence_level": item.get("evidence_level", "estimated"),
        })
    return result


def reconcile_hardware(declared: dict[str, Any], detected: dict[str, Any]) -> dict[str, Any]:
    """Prefer detected values and explicitly preserve declaration discrepancies."""
    d = normalize_hardware(declared)
    a = normalize_hardware(detected)
    discrepancies = {}
    merged = dict(d)
    for key in ("cpu", "ram_gb", "ram_available_gb", "gpu", "vram_gb", "os", "architecture", "backend"):
        if a[key] is not None and a[key] != []:
            if d[key] is not None and d[key] != a[key]:
                discrepancies[key] = {"declared": d[key], "detected": a[key]}
            merged[key] = a[key]
    merged["source"] = "reconciled"
    merged["verification"] = "detected" if not discrepancies else "discrepancy"
    merged["discrepancies"] = discrepancies
    return merged
