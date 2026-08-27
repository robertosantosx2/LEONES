#!/usr/bin/env python3
"""Audit evidence provenance/state without upgrading evidence automatically."""

from __future__ import annotations
import csv, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
OUT = ROOT / "data/prospection/atlas_evidence_audit.csv"
FIELDS = [
    "model_id",
    "model_name",
    "evidence_state",
    "evidence_type",
    "source_url",
    "source_present",
    "retrieved_at",
    "claim_present",
    "action",
    "risk",
]


def url(r):
    for k in ("evidence_url", "source_url", "repository_url"):
        if (r.get(k) or "").strip():
            return r[k].strip()
    return ""


def main():
    with FEED.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    counts = collections.Counter()
    for r in rows:
        u = url(r)
        state = (
            (r.get("evidence_status") or r.get("evidence_state") or "").strip().lower()
        )
        if state not in {"reported", "reproducible", "verified", "rejected"}:
            state = "reported" if u else "unknown"
        et = "external" if u else "unknown"
        risk = (
            "low" if u and state in {"reported", "reproducible", "verified"} else "high"
        )
        action = "retain-and-trace" if u else "needs-source"
        out.append(
            {
                "model_id": r.get("model_id", ""),
                "model_name": r.get("model_name", ""),
                "evidence_state": state,
                "evidence_type": et,
                "source_url": u,
                "source_present": "yes" if u else "no",
                "retrieved_at": r.get("retrieved_at", ""),
                "claim_present": "yes"
                if any(r.get(k) for k in ("evidence_claim", "claim", "notes"))
                else "no",
                "action": action,
                "risk": risk,
            }
        )
        counts[state] += 1
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print("Evidence audit:", dict(counts), "rows=", len(rows), "output=", OUT)


if __name__ == "__main__":
    main()
