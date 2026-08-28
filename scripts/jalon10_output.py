#!/usr/bin/env python3
"""Create a faithful LEONES recommendation output; never re-score or re-decide."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from pathlib import Path

FORBIDDEN = {"score", "ranking_score", "estimated_tps", "tokens_per_second_estimate"}
REQUIRED = ("recommendation_id", "entity", "decision_ref", "evidence_refs", "status", "rationale", "unknowns", "next_action")

def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr); raise SystemExit(1)

def build(rec: dict) -> dict:
    for key in REQUIRED:
        if key not in rec: fail(f"missing recommendation field: {key}")
    leaked = FORBIDDEN.intersection(rec)
    if leaked: fail(f"recommendation contains forbidden parallel metric: {sorted(leaked)}")
    out = {
        "schema": "leones-recommendation-output.v1",
        "output_id": f"out-{rec['recommendation_id']}",
        "recommendation_ref": rec["recommendation_id"],
        "entity": rec["entity"],
        "status": rec["status"],
        "rationale": rec["rationale"],
        "unknowns": rec["unknowns"],
        "next_action": rec["next_action"],
        "decision_ref": rec["decision_ref"],
        "evidence_refs": rec["evidence_refs"],
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if "trace_ref" in rec: out["trace_ref"] = rec["trace_ref"]
    return out

def main(src: str, dst: str) -> None:
    rec = json.loads(Path(src).read_text(encoding="utf-8"))
    if not isinstance(rec, dict): fail("recommendation must be a JSON object")
    Path(dst).write_text(json.dumps(build(rec), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("OK: JALON 10 recommendation output generated")

if __name__ == "__main__":
    if len(sys.argv) != 3: fail("usage: jalon10_output.py RECOMMENDATION.json OUTPUT.json")
    main(sys.argv[1], sys.argv[2])
