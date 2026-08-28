"""Minimal JALON 7 task-result.v1 validation and deterministic aggregation."""

from __future__ import annotations

from typing import Any, Iterable

SCHEMA_VERSION = "task-result.v1"
VALID_STATUSES = {"completed", "failed", "invalid", "not_evaluated"}


def validate_task_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for field in ("task_id", "task_suite", "task_revision", "execution_id", "model_id", "runtime"):
        if not result.get(field):
            errors.append(f"missing required field: {field}")
    status = result.get("completion_status")
    if status not in VALID_STATUSES:
        errors.append("completion_status is invalid")
    if "measurement_status" not in result:
        errors.append("missing required field: measurement_status")
    if not isinstance(result.get("provenance"), dict):
        errors.append("provenance must be an object")
    if status == "completed" and not result.get("benchmark_evidence_id"):
        errors.append("completed task requires benchmark_evidence_id")
    score = result.get("completion_score")
    if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 1):
        errors.append("completion_score must be between 0 and 1")
    return errors


def aggregate_task_results(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(results)
    errors = {r.get("task_id", "<missing>"): validate_task_result(r) for r in items}
    invalid_contract = {task_id: e for task_id, e in errors.items() if e}
    counts = {status: sum(r.get("completion_status") == status for r in items) for status in sorted(VALID_STATUSES)}
    evaluated = counts["completed"] + counts["failed"]
    completed = counts["completed"]
    return {
        "schema_version": "task-set-summary.v1",
        "task_results": [r.get("task_id") for r in items],
        "counts": counts,
        "evaluated_tasks": evaluated,
        "completed_tasks": completed,
        "completion_rate": (completed / evaluated) if evaluated else None,
        "invalid_contract": invalid_contract,
    }


__all__ = ["SCHEMA_VERSION", "VALID_STATUSES", "validate_task_result", "aggregate_task_results"]
