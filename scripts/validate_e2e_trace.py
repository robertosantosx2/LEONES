#!/usr/bin/env python3
"""Validate the minimal LEONES end-to-end trace envelope."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ORDER = ["hardware", "selection", "runtime", "execution", "measurement", "evidence", "decision", "validation", "promotion", "publication", "recommendation"]


def validate(payload: dict) -> None:
    if payload.get("schema") != "leones-e2e-trace.v1":
        raise ValueError("invalid schema")
    if not payload.get("trace_id"):
        raise ValueError("missing trace_id")
    if payload.get("status") not in {"planned", "measured", "published"}:
        raise ValueError("invalid status")
    stages = payload.get("stages")
    if not isinstance(stages, list) or not stages:
        raise ValueError("stages must be a non-empty list")
    names = [item.get("name") for item in stages]
    if len(names) != len(set(names)):
        raise ValueError("duplicate stage")
    if names != sorted(names, key=ORDER.index):
        raise ValueError("stages are out of order")
    for item in stages:
        if item.get("status") not in {"pending", "complete", "skipped"}:
            raise ValueError("invalid stage status")
        if item.get("status") == "complete" and not item.get("ref"):
            raise ValueError("completed stage requires ref")
    complete = {item["name"] for item in stages if item["status"] == "complete"}
    if payload["status"] == "measured" and not {"execution", "measurement", "evidence"} <= complete:
        raise ValueError("measured trace requires execution, measurement and evidence")
    if payload["status"] == "published" and not {"validation", "promotion", "publication"} <= complete:
        raise ValueError("published trace requires validation, promotion and publication")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    validate(json.loads(args.trace.read_text(encoding="utf-8")))
    print("PASS: leones-e2e-trace.v1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
