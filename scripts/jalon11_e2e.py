#!/usr/bin/env python3
"""Build and validate one LEONES E2E operation from existing contract references.

This small program is deliberately boring: it connects identifiers already produced by
LEONES. It does not select a model, run a benchmark, calculate a score, or manufacture
runtime evidence. Think of it as a labelled folder that proves which contract artifact
belongs to each step of one operation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCHEMA = "leones-e2e-operation.v1"
STATUSES = {"planned", "executed", "measured", "recommended", "published"}
FORBIDDEN = {"score", "ranking_score", "estimated_tps", "tokens_per_second_estimate"}
REQUIRED = (
    "operation_id", "selection_ref", "runtime_ref", "execution_ref", "measurement_ref",
    "evidence_refs", "decision_ref", "recommendation_ref", "publication_ref",
    "output_ref", "trace_ref", "status",
)


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def validate(data: dict) -> None:
    if data.get("schema") != SCHEMA:
        fail("invalid schema")
    for key in REQUIRED:
        if key not in data:
            fail(f"missing required field: {key}")
    for key in REQUIRED[:-1]:
        value = data[key]
        if key == "evidence_refs":
            if not isinstance(value, list) or not value or not all(isinstance(x, str) and x for x in value):
                fail("evidence_refs must contain non-empty references")
        elif not isinstance(value, str) or not value.strip():
            fail(f"{key} must be a non-empty reference")
    if data["status"] not in STATUSES:
        fail("invalid status")
    leaked = FORBIDDEN.intersection(data)
    if leaked:
        fail(f"parallel scoring/measurement field present: {sorted(leaked)}")


def build(operation_id: str, refs: dict, status: str) -> dict:
    data = {"schema": SCHEMA, "operation_id": operation_id, **refs, "status": status}
    validate(data)
    return data


def main(src: str, dst: str) -> None:
    source = json.loads(Path(src).read_text(encoding="utf-8"))
    if not isinstance(source, dict):
        fail("input must be a JSON object")
    validate(source)
    Path(dst).write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OK: JALON 11 E2E operation is structurally valid")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        fail("usage: jalon11_e2e.py OPERATION.json OUTPUT.json")
    main(sys.argv[1], sys.argv[2])
