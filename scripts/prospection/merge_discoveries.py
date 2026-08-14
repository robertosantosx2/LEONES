#!/usr/bin/env python3
"""Merge discovery streams before enrichment/classification.

The merge is deliberately source-agnostic: federated forge discoveries are
first-class evidence and must not be lost merely because their host is not
GitHub. Deduplication prefers canonical repository URLs.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def canonical(item: dict) -> str:
    url = (item.get("url") or item.get("evidence_url") or "").strip().rstrip("/").lower()
    if url:
        return url
    return f"{item.get('source','')}:{item.get('name','')}".lower()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--live", default="data/prospection/live_discoveries.ndjson")
    p.add_argument("--federated", default="data/prospection/federated_discoveries.ndjson")
    p.add_argument("--output", default="data/prospection/discovery_input.ndjson")
    args = p.parse_args()

    inputs = [Path(args.live), Path(args.federated)]
    merged = {}
    counts = {}

    for path in inputs:
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            item = json.loads(line)
            key = canonical(item)
            if key not in merged:
                merged[key] = item
                source = item.get("source", "unknown")
                counts[source] = counts.get(source, 0) + 1

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for item in merged.values():
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")

    report = {
        "live_input": str(inputs[0]),
        "federated_input": str(inputs[1]),
        "output": str(output),
        "unique_discoveries": len(merged),
        "unique_by_source": dict(sorted(counts.items())),
        "note": "Discovery streams are merged before enrichment. License Gate remains independent."
    }
    (output.parent / "discovery_merge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
