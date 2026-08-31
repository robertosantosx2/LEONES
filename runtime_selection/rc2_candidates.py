"""Bridge normalized LLMFit candidates into the existing LEONES selection shape."""
from __future__ import annotations

from typing import Any


def to_selection_plan(candidate: dict[str, Any], hardware: dict[str, Any], stack: dict[str, Any]) -> dict[str, Any]:
    """Create one user-selected plan without changing the canonical candidate facts."""
    return {
        "model_id": candidate["model_id"],
        "model": {"id": candidate["model_id"], "name": candidate.get("name", candidate["model_id"]), "revision": candidate.get("revision")},
        "selection_rank": candidate.get("rank"),
        "fit_score": candidate.get("fit"),
        "evidence_level": candidate.get("evidence_level", "estimated"),
        "estimated_tps": candidate.get("estimated_tps"),
        "hardware": hardware,
        "runtime": stack,
        "selection_status": "USER_SELECTED",
        "execution_authorized": False,
        "measurement_required": True,
    }
