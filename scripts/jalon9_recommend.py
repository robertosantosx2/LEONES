#!/usr/bin/env python3
"""Validate a LEONES recommendation without creating a scoring system."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_STATUS = {"recommend", "watch", "reject", "verify_first"}
ALLOWED_NEXT = {"recommend", "verify", "measure", "profile", "watch", "reject"}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


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
