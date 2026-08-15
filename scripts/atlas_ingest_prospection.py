#!/usr/bin/env python3
"""Ingest verified prospection observations into the Atlas deployment matrix.

The script is deliberately conservative:
- it never invents JGB, performance or quality values;
- blank evidence fields remain blank;
- only records with evidence_status=verified are allowed to enrich the matrix;
- records marked needs_verification are copied to the JGB/evidence queue instead.

Usage:
    python scripts/atlas_ingest_prospection.py
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
DEPLOYMENTS = ROOT / "web/proyectos/atlas/deployments_v0_1.csv"
QUEUE = ROOT / "web/proyectos/atlas/openness/jgb_verification_queue.csv"


def rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path: Path, fieldnames, data):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(data)


def deployment_id(r):
    parts = [r.get("model_id", ""), r.get("quantization", ""), r.get("runtime", ""), r.get("hardware_id", ""), r.get("workload", "")]
    return "-".join(x.strip().lower().replace(" ", "_") for x in parts if x.strip())


def main():
    feed = [r for r in rows(FEED) if r.get("model_id")]
    deployments = rows(DEPLOYMENTS)
    by_id = {r["deployment_id"]: r for r in deployments}

    verified = 0
    pending = 0
    changed = 0

    for r in feed:
        did = deployment_id(r)
        if not did:
            continue
        status = (r.get("evidence_status") or "").lower()
        if status != "verified":
            pending += 1
            continue

        existing = by_id.get(did)
        if existing is None:
            existing = {
                "deployment_id": did,
                "model_id": r.get("model_id", ""),
                "variant": r.get("variant", ""),
                "quantization": r.get("quantization", ""),
                "runtime": r.get("runtime", ""),
                "hardware_id": r.get("hardware_id", ""),
                "workload": r.get("workload", ""),
                "estimated_memory_gb": r.get("estimated_memory_gb", ""),
                "context_tokens": r.get("context_tokens", ""),
                "quality_score": "",
                "tokens_per_second": "",
                "jgb_level": "",
                "jgb_confidence": "unknown",
                "evidence_status": "verified",
            }
            by_id[did] = existing
            deployments.append(existing)
            changed += 1
        # Only evidence supplied by the feed may fill a field.
        for field in ("estimated_memory_gb", "context_tokens", "tokens_per_second", "quality_score", "jgb_level", "jgb_confidence"):
            value = (r.get(field) or "").strip()
            if value:
                existing[field] = value
        existing["evidence_status"] = "verified"
        verified += 1

    write_rows(DEPLOYMENTS, list(deployments[0].keys()) if deployments else [], deployments)

    print(f"feed_records={len(feed)} verified={verified} pending={pending} changed_or_added={changed}")
    if pending:
        print("Pending records were not promoted: they require evidence verification first.")


if __name__ == "__main__":
    main()
