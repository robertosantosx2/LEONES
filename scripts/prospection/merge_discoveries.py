#!/usr/bin/env python3
"""Merge discovery streams before enrichment/classification.

The merge is source-agnostic: federated forge discoveries are first-class
 evidence. When the same canonical URL appears in multiple streams, only one
record is emitted, but all source/provenance evidence is preserved.
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


def provenance(item: dict) -> dict:
    p = item.get("provenance") or {}
    return {
        "source": item.get("source"),
        "source_url": item.get("source_url"),
        "evidence_url": item.get("evidence_url") or item.get("url"),
        "adapter": p.get("adapter"),
        "source_id": p.get("source_id") or item.get("source"),
        "query": item.get("query"),
        "observed_at": item.get("observed_at"),
    }


def merge_item(existing: dict, incoming: dict) -> dict:
    sources = existing.setdefault("provenance_records", [])
    records = [r for r in sources if r.get("evidence_url")]
    incoming_record = provenance(incoming)
    if incoming_record.get("evidence_url") not in {r.get("evidence_url") for r in records}:
        records.append(incoming_record)
    existing["provenance_records"] = records
    existing["sources"] = sorted({r.get("source") for r in records if r.get("source")})
    existing["source_count"] = len(existing["sources"])
    # Prefer non-empty metadata while never overwriting useful existing data.
    for field in ("description", "license", "license_spdx", "evidence_url"):
        if not existing.get(field) and incoming.get(field):
            existing[field] = incoming[field]
    return existing


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
                item["provenance_records"] = [provenance(item)]
                item["sources"] = [item.get("source")] if item.get("source") else []
                item["source_count"] = len(item["sources"])
                merged[key] = item
                source = item.get("source", "unknown")
                counts[source] = counts.get(source, 0) + 1
            else:
                merge_item(merged[key], item)

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
        "multi_source_records": sum(1 for x in merged.values() if x.get("source_count", 0) > 1),
        "note": "Duplicate canonical URLs collapse to one record while all provenance records are preserved. License Gate remains independent."
    }
    (output.parent / "discovery_merge_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
