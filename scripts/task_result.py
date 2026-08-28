"""Minimal JALON 7 task-result.v1 validation and deterministic aggregation."""

from __future__ import annotations

from typing import Any, Iterable

SCHEMA_VERSION = "task-result.v1"
SUMMARY_SCHEMA_VERSION = "task-set-summary.v1"
VALID_STATUSES = {"completed", "failed", "invalid", "not_evaluated"}


def validate_task_result(result: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if result.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for field in (
        "task_id",
        "task_suite",
        "task_revision",
        "execution_id",
        "model_id",
        "runtime",
    ):
        if not result.get(field):
            errors.append(f"missing required field: {field}")
    status = result.get("completion_status")
    if status not in VALID_STATUSES:
        errors.append("completion_status is invalid")
    if not result.get("measurement_status"):
        errors.append("measurement_status is missing or empty")
    if not isinstance(result.get("provenance"), dict):
        errors.append("provenance must be an object")
    if status == "completed" and not result.get("benchmark_evidence_id"):
        errors.append("completed task requires benchmark_evidence_id")
    score = result.get("completion_score")
    if score is not None and (
        not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= score <= 1
    ):
        errors.append("completion_score must be between 0 and 1")
    return errors


def task_result_from_runtime_benchmark(
    benchmark: dict[str, Any],
    *,
    task_id: str,
    task_suite: str,
    task_revision: str,
    completion_status: str,
    completion_score: float | None = None,
) -> dict[str, Any]:
    """Project one measured runtime benchmark into task-result.v1.

    This is a projection only: it never invents execution provenance. A
    benchmark without the identifiers required by J7 is rejected instead of
    being upgraded by inference.
    """
    schema = benchmark.get("schema_version") or benchmark.get("schema")
    if schema != "runtime-benchmark.v1":
        raise ValueError("unsupported benchmark artifact")
    execution_id = benchmark.get("execution_id")
    runtime = benchmark.get("runtime")
    model_id = benchmark.get("model_id") or benchmark.get("model")
    if not execution_id or not runtime or not model_id:
        raise ValueError("runtime benchmark lacks execution identity")
    evidence_id = benchmark.get("benchmark_evidence_id") or benchmark.get("evidence_id")
    if completion_status == "completed" and not evidence_id:
        raise ValueError("completed task requires benchmark evidence identity")
    result = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "task_suite": task_suite,
        "task_revision": task_revision,
        "execution_id": execution_id,
        "benchmark_evidence_id": evidence_id,
        "model_id": model_id,
        "model_revision": benchmark.get("model_revision"),
        "runtime": runtime,
        "runtime_version": benchmark.get("runtime_version"),
        "hardware": benchmark.get("hardware", {}),
        "workload": benchmark.get("workload", {}),
        "completion_status": completion_status,
        "completion_score": completion_score,
        "measurement_status": benchmark.get("measurement_status") or benchmark.get("status"),
        "provenance": {
            "source": "runtime-benchmark.v1",
            "execution_id": execution_id,
            "benchmark_evidence_id": evidence_id,
        },
    }
    errors = validate_task_result(result)
    if errors:
        raise ValueError("invalid projected task result: " + "; ".join(errors))
    return result


def aggregate_task_results(results: Iterable[dict[str, Any]]) -> dict[str, Any]:
    items = list(results)
    errors = {
        r.get("task_id", "<missing>"): validate_task_result(r) for r in items
    }
    invalid_contract = {task_id: e for task_id, e in errors.items() if e}
    valid_items = [r for r in items if not validate_task_result(r)]
    counts = {
        status: sum(r.get("completion_status") == status for r in valid_items)
        for status in sorted(VALID_STATUSES)
    }
    evaluated = counts["completed"] + counts["failed"]
    completed = counts["completed"]
    return {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        "task_results": [r.get("task_id") for r in items],
        "benchmark_evidence_ids": [
            r.get("benchmark_evidence_id") for r in items if r.get("benchmark_evidence_id")
        ],
        "counts": counts,
        "evaluated_tasks": evaluated,
        "completed_tasks": completed,
        "completion_rate": (completed / evaluated) if evaluated else None,
        "invalid_contract": invalid_contract,
    }


__all__ = [
    "SCHEMA_VERSION",
    "SUMMARY_SCHEMA_VERSION",
    "VALID_STATUSES",
    "validate_task_result",
    "task_result_from_runtime_benchmark",
    "aggregate_task_results",
]
