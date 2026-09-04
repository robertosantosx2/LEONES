"""External model evidence used to inform, never replace, LEONES selection."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "model-evidence.v1"


def _memory_estimate_gb(parameters_b: float, bits: int, overhead_gb: float = 0.4) -> float:
    """Conservative rough weight+runtime estimate; not a measured footprint."""
    return round(parameters_b * bits / 8 + overhead_gb, 3)


def enrich_candidates(
    hardware: dict[str, Any],
    candidates: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach HF/Artificial Analysis evidence and rank candidates deterministically.

    External speed is explicitly named hosted_output_tps and is never treated as
    a local benchmark. The result contains a recommendation, not user selection.
    """
    by_id = {item["model_id"]: item for item in evidence if item.get("model_id")}
    available_gb = float(hardware.get("ram", {}).get("available_gb", hardware.get("ram_available_gb", 0)) or 0)
    enriched = []
    for candidate in candidates:
        item = dict(candidate)
        info = by_id.get(candidate.get("model_id"), {})
        item["external_evidence"] = {
            "hugging_face": info.get("hugging_face"),
            "artificial_analysis": info.get("artificial_analysis"),
        }
        params = info.get("parameters_b") or candidate.get("parameters")
        bits = info.get("quantization_bits", 4)
        estimate = _memory_estimate_gb(float(params), int(bits)) if params else None
        item["local_fit_estimate"] = {
            "estimated_model_memory_gb": estimate,
            "available_ram_gb": available_gb,
            "estimated_headroom_gb": round(available_gb - estimate, 3) if estimate is not None else None,
            "status": "fit" if estimate is not None and available_gb >= estimate else "marginal_or_unknown",
        }
        aa = info.get("artificial_analysis") or {}
        score = float(aa.get("intelligence_index", 0) or 0)
        fit_bonus = 1 if item["local_fit_estimate"]["status"] == "fit" else 0
        item["decision_score"] = round(fit_bonus * 100 + score, 3)
        item["evidence_status"] = "external_only"
        enriched.append(item)

    enriched.sort(key=lambda x: (-x["decision_score"], x["model_id"]))
    for rank, item in enumerate(enriched, 1):
        item["decision_rank"] = rank

    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_policy": "EXTERNAL_EVIDENCE_INFORMS_SELECTION; LEONES_MEASUREMENT_REMAINS_AUTHORITATIVE",
        "hardware": hardware,
        "candidates": enriched,
        "recommended_model_id": enriched[0]["model_id"] if enriched else None,
        "user_choice_required": True,
        "execution_authorized": False,
        "measured": False,
    }
