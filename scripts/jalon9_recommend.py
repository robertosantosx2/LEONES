#!/usr/bin/env python3
"""Validate one canonical LEONES recommendation.

This guard validates the existing recommendation contract. It does not rank
models, benchmark them, or invent measurements. JALON 7 task summaries may be
attached as auditable context without changing recommendation semantics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_STATUS = {"recommend", "watch", "reject", "verify_first"}
ALLOWED_NEXT = {"recommend", "verify", "measure", "profile", "watch", "reject"}
TASK_SUMMARY_SCHEMA = "task-set-summary.v1"
TASK_STATUSES = {"completed", "failed", "invalid", "not_evaluated"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_task_summary(summary: dict[str, Any]) -> None:
    """Validate the minimum JALON 7 summary shape without scoring it."""
    if summary.get("schema_version") != TASK_SUMMARY_SCHEMA:
        raise ValueError(f"task summary schema must be {TASK_SUMMARY_SCHEMA}")
    counts = summary.get("counts")
    if not isinstance(counts, dict) or set(counts) != TASK_STATUSES:
        raise ValueError("task summary counts must contain all task statuses")
    if not all(isinstance(value, int) and not isinstance(value, bool) and value >= 0 for value in counts.values()):
        raise ValueError("task summary counts must be non-negative integers")
    evaluated = summary.get("evaluated_tasks")
    completed = summary.get("completed_tasks")
    if not isinstance(evaluated, int) or evaluated < 0 or not isinstance(completed, int) or completed < 0:
        raise ValueError("task summary totals must be non-negative integers")
    if evaluated != counts["completed"] + counts["failed"]:
        raise ValueError("evaluated_tasks must equal completed plus failed")
    if completed != counts["completed"]:
        raise ValueError("completed_tasks must equal completed count")
    if not isinstance(summary.get("task_results"), list):
        raise ValueError("task_results must be an array")
    evidence_ids = summary.get("benchmark_evidence_ids")
    if not isinstance(evidence_ids, list) or not all(isinstance(value, str) and value for value in evidence_ids):
        raise ValueError("benchmark_evidence_ids must be an array of references")
    if summary.get("completion_rate") is not None:
        rate = summary["completion_rate"]
        if not isinstance(rate, (int, float)) or isinstance(rate, bool) or not 0 <= rate <= 1:
            raise ValueError("completion_rate must be between 0 and 1")


def attach_task_summary(
    recommendation: dict[str, Any],
    summary: dict[str, Any],
    *,
    task_summary_ref: str,
) -> dict[str, Any]:
    """Attach JALON 7 summary provenance without changing recommendation status."""
    if not isinstance(task_summary_ref, str) or not task_summary_ref.strip():
        raise ValueError("task_summary_ref cannot be empty")
    validate_task_summary(summary)
    enriched = dict(recommendation)
    enriched["task_summary_ref"] = task_summary_ref
    return enriched


def validate(data: dict) -> None:
    required = (
        "schema", "recommendation_id", "entity", "decision_ref",
        "evidence_refs", "status", "rationale", "unknowns", "next_action"
    )
    for key in required:
        if key not in data:
            fail(f"missing required field: {key}")
    if data["schema"] != "leones-recommendation.v1":
        fail("invalid schema")
    if not isinstance(data["recommendation_id"], str) or len(data["recommendation_id"]) < 8:
        fail("invalid recommendation_id")
    if not isinstance(data["entity"], str) or not data["entity"].strip():
        fail("entity cannot be empty")
    if not isinstance(data["decision_ref"], str) or not data["decision_ref"].strip():
        fail("decision_ref cannot be empty")
    if not isinstance(data["evidence_refs"], list) or not all(isinstance(x, str) and x for x in data["evidence_refs"]):
        fail("evidence_refs must be an array of non-empty references")
    if data["status"] not in ALLOWED_STATUS:
        fail("invalid status")
    if not isinstance(data["rationale"], str) or not data["rationale"].strip():
        fail("rationale cannot be empty")
    if not isinstance(data["unknowns"], list) or not all(isinstance(x, str) for x in data["unknowns"]):
        fail("unknowns must be an array of strings")
    if data["next_action"] not in ALLOWED_NEXT:
        fail("invalid next_action")
    if "task_summary_ref" in data and (not isinstance(data["task_summary_ref"], str) or not data["task_summary_ref"].strip()):
        fail("task_summary_ref cannot be empty")

    if data["status"] == "recommend":
        if data.get("minimum_evidence_met") is not True:
            fail("recommendation blocked: minimum_evidence_met must be true")
        if data["next_action"] != "recommend":
            fail("recommendation blocked: next_action must be recommend")
        if not data["evidence_refs"]:
            fail("recommendation requires evidence_refs")
    elif data["status"] == "verify_first":
        if data["next_action"] not in {"verify", "measure", "profile"}:
            fail("verify_first requires verify, measure or profile as next_action")
        if not data["unknowns"]:
            fail("verify_first requires explicit unknowns")
    elif data["status"] == "watch" and data["next_action"] != "watch":
        fail("watch requires next_action=watch")
    elif data["status"] == "reject" and data["next_action"] != "reject":
        fail("reject requires next_action=reject")

    forbidden = {"score", "tokens_per_second_estimate", "estimated_tps", "ranking_score"}
    leaked = forbidden.intersection(data)
    if leaked:
        fail(f"parallel scoring/measurement field present: {sorted(leaked)}")


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("recommendation must be a JSON object")
    validate(data)
    print("OK: JALON 9 recommendation is structurally valid")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: jalon9_recommend.py FILE.json")
    main(sys.argv[1])
