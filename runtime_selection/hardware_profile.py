"""RC2 hardware profile normalization and model-candidate bridge.

This module deliberately does not benchmark hardware or invent compatibility data.
It normalizes declared/detected facts and preserves source/provenance.
"""
from __future__ import annotations

from typing import Any

UNKNOWN = None


def normalize_hardware(source: dict[str, Any]) -> dict[str, Any]:
    """Return the canonical RC2 hardware profile without fabricating values."""
    return {
        "cpu": source.get("cpu", UNKNOWN),
        "ram_gb": source.get("ram_gb", UNKNOWN),
        "gpu": source.get("gpu", UNKNOWN),
        "vram_gb": source.get("vram_gb", UNKNOWN),
        "os": source.get("os", UNKNOWN),
        "architecture": source.get("architecture", UNKNOWN),
        "accelerators": source.get("accelerators", []),
        "source": source.get("source", "unknown"),
        "source_version": source.get("source_version", UNKNOWN),
        "verification": source.get("verification", "declared"),
    }


def normalize_candidates(raw: list[dict[str, Any]], *, source: str = "llmfit") -> list[dict[str, Any]]:
    """Normalize LLMFit candidates while retaining ranking/evidence provenance."""
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
    for key in ("cpu", "ram_gb", "gpu", "vram_gb", "os", "architecture"):
        if a[key] is not None:
            if d[key] is not None and d[key] != a[key]:
                discrepancies[key] = {"declared": d[key], "detected": a[key]}
            merged[key] = a[key]
    merged["source"] = "reconciled"
    merged["verification"] = "detected" if not discrepancies else "discrepancy"
    merged["discrepancies"] = discrepancies
    return merged
