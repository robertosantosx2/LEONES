"""Convert runtime evidence into a conservative Router ranking signal."""
from __future__ import annotations

from datetime import datetime, timezone
from math import exp


def recency_weight(observed_at: str, half_life_days: float = 30.0, now: datetime | None = None) -> float:
    if not observed_at:
        return 0.0
    now = now or datetime.now(timezone.utc)
    observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    age_days = max(0.0, (now - observed).total_seconds() / 86400.0)
    return exp(-0.69314718056 * age_days / half_life_days)


def ranking_signal(evidence: dict, *, target_tps: float = 10.0, half_life_days: float = 30.0) -> dict:
    """Return a Router signal; estimates never count as measured evidence."""
    if evidence.get("evidence_status") != "measured":
        return {"source": "runtime_evidence", "status": "ignored", "score": 0.0}
    tps = evidence.get("tokens_per_second")
    if not isinstance(tps, (int, float)) or tps < 0:
        return {"source": "runtime_evidence", "status": "invalid", "score": 0.0}
    throughput = min(1.0, tps / target_tps) if target_tps > 0 else 0.0
    freshness = recency_weight(evidence.get("observed_at", ""), half_life_days)
    score = round(throughput * freshness, 6)
    return {
        "source": "runtime_evidence",
        "status": "measured",
        "score": score,
        "tokens_per_second": tps,
        "freshness": round(freshness, 6),
        "target_tps": target_tps,
        "measurement_scope": evidence.get("measurement_scope"),
    }


def rank_candidates(candidates: list[dict], evidence_by_model: dict[str, dict]) -> list[dict]:
    """Add measured evidence without replacing the candidate's estimated fields."""
    ranked = []
    for candidate in candidates:
        model_id = candidate.get("model_id") or candidate.get("name")
        signal = ranking_signal(evidence_by_model.get(model_id, {}))
        item = dict(candidate)
        item["runtime_evidence"] = signal
        item["measured_tps"] = (evidence_by_model.get(model_id) or {}).get("tokens_per_second") if signal["status"] == "measured" else None
        ranked.append(item)
    return sorted(ranked, key=lambda x: (x["runtime_evidence"]["score"], x.get("estimated_tps") or 0), reverse=True)
