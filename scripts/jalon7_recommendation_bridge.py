#!/usr/bin/env python3
"""Project a JALON 7 task-set summary into the canonical recommendation boundary.

Adapter only: it consumes the existing task-result aggregation and does not
create a second classifier, scorer, selector, or benchmark.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

VALID_STATUSES = {"completed", "failed", "invalid", "not_evaluated"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        fail("task summary must be a JSON object")
    if data.get("schema_version") != "task-set-summary.v1":
        fail("input must use task-set-summary.v1")
    for key in ("task_results", "benchmark_evidence_ids", "counts"):
        if key not in data:
            fail(f"missing required field: {key}")
    if not isinstance(data["task_results"], list):
        fail("task_results must be an array")
    if not isinstance(data["benchmark_evidence_ids"], list):
        fail("benchmark_evidence_ids must be an array")
    counts = data["counts"]
    if not isinstance(counts, dict):
        fail("counts must be an object")
    for status in VALID_STATUSES:
        if not isinstance(counts.get(status), int) or counts[status] < 0:
            fail(f"counts.{status} must be a non-negative integer")

    evaluated = counts["completed"] + counts["failed"]
    completed = counts["completed"]
    evidence_refs = sorted({x for x in data["benchmark_evidence_ids"] if isinstance(x, str) and x})
    minimum_evidence_met = evaluated > 0 and completed > 0 and counts["invalid"] == 0
    unknowns: list[str] = []
    if counts["not_evaluated"]:
        unknowns.append("one or more tasks were not evaluated")
    if counts["failed"]:
        unknowns.append("one or more evaluated tasks failed")
    if counts["invalid"]:
        unknowns.append("one or more task results are invalid")
    if not evidence_refs:
        unknowns.append("no benchmark evidence reference is available")

    status = "recommend" if minimum_evidence_met else "verify_first"
    result = {
        "schema": "leones-recommendation.v1",
        "recommendation_id": "j7-bridge-" + Path(path).stem,
        "entity": "task-set",
        "decision_ref": "j7-task-summary",
        "evidence_refs": evidence_refs,
        "status": status,
        "rationale": (
            "JALON 7 summary contains completed evaluated tasks, no invalid results, and canonical evidence references."
            if minimum_evidence_met
            else "JALON 7 summary is insufficient for recommendation; verification is required."
        ),
        "unknowns": unknowns,
        "next_action": "recommend" if minimum_evidence_met else "verify",
        "minimum_evidence_met": minimum_evidence_met,
        "trace_ref": str(data.get("trace_ref") or "j7-task-summary"),
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: jalon7_recommendation_bridge.py TASK-SET-SUMMARY.json")
    main(sys.argv[1])
