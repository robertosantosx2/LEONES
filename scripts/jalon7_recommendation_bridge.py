#!/usr/bin/env python3
"""Project JALON 7 task summary into the canonical recommendation boundary.

This is deliberately an adapter, not a second classifier or scorer. It consumes
an existing task-set summary and emits only the fields needed by the existing
recommendation contract. Runtime performance remains owned by runtime evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_STATUSES = {"completed", "failed", "invalid", "not_evaluated"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("task summary must be a JSON object")

    required = ("schema", "tasks")
    for key in required:
        if key not in data:
            fail(f"missing required field: {key}")
    if data["schema"] != "task-set-summary.v1":
        fail("input must use task-set-summary.v1")
    if not isinstance(data["tasks"], list) or not data["tasks"]:
        fail("tasks must be a non-empty array")

    counts = {status: 0 for status in ALLOWED_STATUSES}
    evidence_refs: list[str] = []
    for task in data["tasks"]:
        if not isinstance(task, dict):
            fail("each task must be an object")
        status = task.get("status")
        if status not in ALLOWED_STATUSES:
            fail(f"invalid task status: {status!r}")
        counts[status] += 1
        if status != "not_evaluated":
            ref = task.get("benchmark_evidence_id")
            if isinstance(ref, str) and ref:
                evidence_refs.append(ref)

    evaluated = counts["completed"] + counts["failed"] + counts["invalid"]
    minimum_evidence_met = evaluated > 0 and counts["invalid"] == 0 and counts["completed"] > 0
    status = "recommend" if minimum_evidence_met else "verify_first"
    next_action = "recommend" if status == "recommend" else "verify"
    unknowns = []
    if counts["not_evaluated"]:
        unknowns.append("one or more tasks were not evaluated")
    if counts["failed"]:
        unknowns.append("one or more evaluated tasks failed")
    if counts["invalid"]:
        unknowns.append("one or more task results are invalid")

    result = {
        "schema": "leones-recommendation.v1",
        "recommendation_id": "j7-bridge-" + str(data.get("summary_id", "summary")),
        "entity": str(data.get("entity", "task-set")),
        "decision_ref": str(data.get("decision_ref", "j7-task-summary")),
        "evidence_refs": sorted(set(evidence_refs)),
        "status": status,
        "rationale": (
            "Task-set evidence contains completed tasks and no invalid results."
            if minimum_evidence_met
            else "Task-set evidence is insufficient for recommendation; verification is required."
        ),
        "unknowns": unknowns,
        "next_action": next_action,
        "minimum_evidence_met": minimum_evidence_met,
        "trace_ref": str(data.get("trace_ref", "")),
        "task_counts": counts,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: jalon7_recommendation_bridge.py TASK-SET-SUMMARY.json")
    main(sys.argv[1])
