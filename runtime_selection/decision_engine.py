"""RC3 explainable multi-criteria model decision engine."""
from __future__ import annotations
from typing import Any

SCHEMA_VERSION = "model-decision.v1"
PROFILES: dict[str, dict[str, float]] = {
    "balanced": {"intelligence": .40, "fit": .35, "context": .10, "availability": .10, "reasoning": .05},
    "quality": {"intelligence": .65, "fit": .15, "context": .10, "availability": .05, "reasoning": .05},
    "speed": {"intelligence": .20, "fit": .60, "context": .05, "availability": .10, "reasoning": .05},
    "memory": {"intelligence": .15, "fit": .70, "context": .05, "availability": .05, "reasoning": .05},
    "long_context": {"intelligence": .25, "fit": .25, "context": .40, "availability": .05, "reasoning": .05},
    "reasoning": {"intelligence": .45, "fit": .25, "context": .10, "availability": .05, "reasoning": .15},
}

def _norm(value: float | None, maximum: float) -> float:
    return 0.0 if value is None or maximum <= 0 else max(0.0, min(1.0, value / maximum))

def _available_ram(hardware: dict[str, Any]) -> float:
    ram = hardware.get("ram") or {}
    return float(ram.get("available_gb") or ram.get("total_gb") or hardware.get("ram_available_gb") or hardware.get("ram_gb") or 0)

def _memory_estimate(item: dict[str, Any]) -> float | None:
    params = item.get("parameters_b")
    if params is None: return None
    return round(float(params) * int(item.get("quantization_bits") or 4) / 8 + .4, 3)

def _fit(item: dict[str, Any], available_ram_gb: float) -> tuple[float, str, float | None]:
    estimate = _memory_estimate(item)
    if estimate is None or available_ram_gb <= 0: return .20, "unknown", None
    headroom = round(available_ram_gb - estimate, 3)
    if headroom >= max(.5, available_ram_gb * .20):
        return max(.55, min(1.0, .65 + headroom / max(available_ram_gb * 2, 1))), "fit", headroom
    if headroom >= 0: return .35, "marginal", headroom
    return .05, "insufficient", headroom

def decide_models(enriched: dict[str, Any], profile: str = "balanced", hardware: dict[str, Any] | None = None) -> dict[str, Any]:
    """Rank proposals against the supplied physical hardware; never authorizes or measures."""
    if profile not in PROFILES: raise ValueError(f"unknown decision profile: {profile}")
    hardware = hardware or enriched.get("hardware") or {}
    weights = PROFILES[profile]; candidates = enriched.get("candidates", []); available_ram_gb = _available_ram(hardware)
    max_i = max([float((c.get("external_evidence") or {}).get("artificial_analysis", {}).get("intelligence_index", 0) or 0) for c in candidates] or [1])
    max_c = max([float((c.get("external_evidence") or {}).get("artificial_analysis", {}).get("context_tokens", 0) or 0) for c in candidates] or [1])
    scored = []
    for candidate in candidates:
        item = dict(candidate); aa = ((item.get("external_evidence") or {}).get("artificial_analysis") or {}); hf = ((item.get("external_evidence") or {}).get("hugging_face") or {})
        fit, fit_status, headroom = _fit(item, available_ram_gb)
        factors = {"intelligence": _norm(float(aa.get("intelligence_index", 0) or 0), max_i), "fit": fit, "context": _norm(float(aa.get("context_tokens", 0) or 0), max_c), "availability": 1.0 if hf.get("status") == "weights_available" else .5 if hf.get("status") == "gated" else 0.0, "reasoning": 1.0 if aa.get("reasoning") else 0.0}
        item["decision_score"] = round(sum(weights[k] * factors[k] for k in weights) * 100, 3)
        item["decision_factors"] = {k: round(v, 3) for k, v in factors.items()}
        item["local_fit_estimate"] = {"estimated_model_memory_gb": _memory_estimate(item), "available_ram_gb": available_ram_gb, "estimated_headroom_gb": headroom, "status": fit_status}
        item["decision_profile"] = profile; item["evidence_status"] = "external_only"; item["selection_status"] = "CANDIDATE"
        scored.append(item)
    scored.sort(key=lambda x: (-x["decision_score"], x["model_id"]))
    for rank, item in enumerate(scored, 1): item["decision_rank"] = rank
    return {"schema_version": SCHEMA_VERSION, "profile": profile, "weights": weights, "hardware": hardware, "candidates": scored, "recommended_model_id": scored[0]["model_id"] if scored else None, "user_choice_required": True, "selected_model_id": None, "execution_authorized": False, "measured": False, "measurement_required": True, "recommendation_authority": "external_evidence_plus_detected_hardware_estimate; LEONES_MEASUREMENT_FINAL"}
