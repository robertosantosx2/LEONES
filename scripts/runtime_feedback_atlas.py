#!/usr/bin/env python3
"""Apply measured runtime evidence to the recommendation feed without fabricating data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEED = ROOT / "data/prospection/atlas_feed.csv"
DEFAULT_FEEDBACK = ROOT / "data/prospection/runtime_feedback.jsonl"


def load_feedback(path: Path) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return latest
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            item = json.loads(line)
            model_id = item.get("model_id")
            if not model_id:
                continue
            latest[model_id] = item
    return latest


def apply_feedback(
    rows: list[dict[str, str]], feedback: dict[str, dict[str, Any]]
) -> list[dict[str, str]]:
    result = []
    for row in rows:
        out = dict(row)
        model_id = row.get("model_id") or row.get("model_name")
        item = feedback.get(model_id)
        if item and item.get("evidence_type") == "measured":
            metrics = item.get("metrics") or {}
            tps = metrics.get("measured_tps")
            if tps is not None:
                out["tokens_per_second"] = str(tps)
                out["performance_evidence_type"] = "measured"
                out["performance_evidence_id"] = item.get("execution_id", "")
                out["performance_evidence_source"] = (item.get("provenance") or {}).get(
                    "source", ""
                )
                out["performance_evidence_at"] = (item.get("provenance") or {}).get(
                    "measured_at", ""
                )
        result.append(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--feedback", type=Path, default=DEFAULT_FEEDBACK)
    parser.add_argument("--out", type=Path, default=DEFAULT_FEED)
    args = parser.parse_args()
    with args.feed.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
        fields = list(fh.fieldnames or [])
    rows = apply_feedback(rows, load_feedback(args.feedback))
    for field in (
        "performance_evidence_type",
        "performance_evidence_id",
        "performance_evidence_source",
        "performance_evidence_at",
    ):
        if field not in fields:
            fields.append(field)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
