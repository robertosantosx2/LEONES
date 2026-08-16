#!/usr/bin/env python3
"""Validate the LEONES recommendation gate without inventing evidence."""
import json
import sys
from pathlib import Path

ALLOWED_DECISIONS = {"recommend", "watch", "reject", "verify_first"}
ALLOWED_NEXT = {"recommend", "verify", "measure", "profile", "watch", "reject"}


def fail(message):
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for key in ("entity", "evidence_profile", "decision", "rationale", "unknowns", "next_action"):
        if key not in data:
            fail(f"missing required field: {key}")
    if not data["entity"].strip():
        fail("entity cannot be empty")
    if data["decision"] not in ALLOWED_DECISIONS:
        fail("invalid decision")
    if data["next_action"] not in ALLOWED_NEXT:
        fail("invalid next_action")
    if not isinstance(data["unknowns"], list):
        fail("unknowns must be an array")

    if data["decision"] == "recommend":
        if data.get("minimum_evidence_met") is not True:
            fail("recommendation blocked: minimum_evidence_met must be true")
        if data["next_action"] != "recommend":
            fail("recommendation blocked: next_action must be recommend")

    if data.get("external_scores_used") is True and not data.get("evidence_profile"):
        fail("external score has no evidence profile")

    print("OK: recommendation gate is structurally valid")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        fail("usage: validate_recommendation_gate.py FILE.json")
    main(sys.argv[1])
