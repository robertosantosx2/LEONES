"""RC3 explainable multi-criteria model decision engine."""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "model-decision.v1"

PROFILES: dict[str, dict[str, float]] = {
    "balanced": {"intelligence": 0.40, "fit": 0.35, "context": 0.10, "availability": 0.10, "reasoning": 0.05},
    "quality": {"intelligence": 0.65, "fit": 0.15, "context": 0.10, "availability": 0.05, "reasoning": 0.05},
    "speed": {"intelligence": 0.20, "fit": 0.60, "context": 0.05, "availability": 0.10, "reasoning": 0.05},
    "memory": {"intelligence": 0.15, "fit": 0.70, "context": 0.05, "availability": 0.05, "reasoning": 0.05},
    "long_context": {"intelligence": 0.25, "fit": 0.25, "context": 0.40, "availability": 0.05, "reasoning": 0.05},
    "reasoning": {"intelligence": 0.45, "fit": 0.25, "context": 0.10, "availability": 0.05, "reasoning": 0.15},
}


def _norm(value: float | None, maximum: float) -> float:
    if value is None or maximum <= 0:
        return 0.0
    return max(0.0, min(1.0, value / maximum))


def _fit_score(item: dict[str, Any]) -> float:
    fit = item.get("local_fit_estimate") or {}
    status = fit.get("status")
    headroom = fit.get("estimated_headroom_gb")
    if status == "fit" and headroom is not None:
        return max(0.55, min(1.0, 0.65 + float(headroom) / 8.0))
    return 0.20 if status == "marginal_or_unknown" else 0.0


def decide_models(enriched: dict[str, Any], profile: str = "balanced") -> dict[str, Any]:
    """Rank candidates without selecting or authorizing execution."""
    if profile not in PROFILES:
        raise ValueError(f"unknown decision profile: {profile}")
    weights = PROFILES[profile]
    candidates = enriched.get("candidates", [])
    max_intelligence = max([float((c.get("external_evidence") or {}).get("artificial_analysis", {}).get("intelligence_index", 0) or 0) for c in candidates] or [1])
    max_context = max([float((c.get("external_evidence") or {}).get("artificial_analysis", {}).get("context_tokens", 0) or 0) for c in candidates] or [1])
    scored: list[dict[str, Any]] = []
    for candidate in candidates:
        item = dict(candidate)
        aa = ((item.get("external_evidence") or {}).get("artificial_analysis") or {})
        hf = ((item.get("external_evidence") or {}).get("hugging_face") or {})
        intelligence = _norm(float(aa.get("intelligence_index", 0) or 0), max_intelligence)
        context = _norm(float(aa.get("context_tokens", 0) or 0), max_context)
        fit = _fit_score(item)
        availability = 1.0 if hf.get("status") == "weights_available" else 0.5 if hf.get("status") == "gated" else 0.0
        reasoning = 1.0 if aa.get("reasoning") else 0.0
        score = sum(weights[key] * value for key, value in {"intelligence": intelligence, "fit": fit, "context": context, "availability": availability, "reasoning": reasoning}.items())
        item["decision_score"] = round(score * 100, 3)
        item["decision_factors"] = {"intelligence": round(intelligence, 3), "fit": round(fit, 3), "context": round(context, 3), "availability": round(availability, 3), "reasoning": round(reasoning, 3)}
        item["decision_profile"] = profile
        item["evidence_status"] = "external_only"
        scored.append(item)
    scored.sort(key=lambda item: (-item["decision_score"], item["model_id"]))
    for rank, item in enumerate(scored, 1):
        item["decision_rank"] = rank
    return {
        "schema_version": SCHEMA_VERSION,
        "profile": profile,
        "weights": weights,
        "candidates": scored,
        "recommended_model_id": scored[0]["model_id"] if scored else None,
        "user_choice_required": True,
        "execution_authorized": False,
        "measured": False,
        "recommendation_authority": "external_evidence_plus_hardware_estimate; LEONES_MEASUREMENT_FINAL",
    }
