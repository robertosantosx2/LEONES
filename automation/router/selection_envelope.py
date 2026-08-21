"""Canonical envelope passed from model/runtime selection into task execution."""
from __future__ import annotations

from datetime import datetime, timezone


def build_selection_envelope(selected: dict, *, task_id: str, use_case: str | None = None) -> dict:
    """Freeze the selector decision before an executor consumes it."""
    if not selected:
        raise ValueError("cannot build an execution envelope without a selected candidate")
    model_id = selected.get("model_id")
    runtime = selected.get("runtime")
    if not model_id or not runtime:
        raise ValueError("selected candidate must contain model_id and runtime")
    return {
        "schema_version": "leones.runtime-selection.v1",
        "selection_status": "selected",
        "task_id": task_id,
        "use_case": use_case,
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "model_id": model_id,
        "runtime": runtime,
        "runtime_command": selected.get("runtime_command"),
        "best_quant": selected.get("best_quant"),
        "estimated_tps": selected.get("estimated_tps"),
        "measured_tps": selected.get("measured_tps"),
        "evidence_status": selected.get("runtime_evidence", {}).get("status", "ignored"),
        "candidate_id": selected.get("candidate_id"),
        "selection_reason": (
            "measured-runtime-evidence" if selected.get("runtime_evidence", {}).get("status") == "measured"
            else "llmfit-estimate-fallback"
        ),
    }
