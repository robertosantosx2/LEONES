"""Final LEONES model/runtime selector.

LLMFit provides eligibility and estimates; measured runtime evidence is an
additional signal. Neither source is silently rewritten into the other.
"""
from __future__ import annotations

from .runtime_evidence import ranking_signal


def select(candidates: list[dict], evidence_by_model: dict[str, dict] | None = None,
           *, target_tps: float = 10.0, require_runtime: bool = True,
           require_installed: bool = False) -> dict | None:
    evidence_by_model = evidence_by_model or {}
    eligible = []
    for candidate in candidates:
        if candidate.get("fit_level") not in {"perfect", "good"}:
            continue
        if require_runtime and not candidate.get("runtime_available", False):
            continue
        if require_installed and not candidate.get("installed", False):
            continue
        evidence = evidence_by_model.get(candidate.get("model_id"), {})
        signal = ranking_signal(evidence, target_tps=target_tps)
        item = dict(candidate)
        item["runtime_evidence"] = signal
        item["measured_tps"] = evidence.get("tokens_per_second") if signal["status"] == "measured" else None
        eligible.append(item)
    if not eligible:
        return None
    # Measured evidence is authoritative when present; otherwise fall back to
    # deterministic LLMFit ordering without fabricating measurements.
    eligible.sort(key=lambda x: (
        x["runtime_evidence"]["status"] == "measured",
        x["runtime_evidence"]["score"],
        x.get("score") if x.get("score") is not None else -1,
        x.get("estimated_tps") if x.get("estimated_tps") is not None else -1,
    ), reverse=True)
    return eligible[0]
