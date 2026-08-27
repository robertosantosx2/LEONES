#!/usr/bin/env python3
"""Merge deterministic recommendation dimensions into an existing CSV.

Existing recommendation columns are preserved. Missing enrichment fields are
added. Unknown values remain unknown; this layer does not infer CABE, RULA,
JGB, performance, or evidence state from unrelated scores.
"""

from __future__ import annotations
import argparse, csv

ENRICH_FIELDS = [
    "model_id",
    "model_name",
    "hardware_id",
    "fit_score",
    "cabe",
    "cabe_status",
    "rula",
    "rula_status",
    "jgb_level",
    "jgb_status",
    "tokens_per_second",
    "performance_score",
    "economic_score",
    "uncertainty",
    "parameters_total_b",
    "parameters_active_b",
    "quantization",
    "weight_memory_gb",
    "kv_cache_gb",
    "runtime_overhead_gb",
    "memory_margin_gb",
    "runtime",
    "runtime_version",
    "backend",
    "context_length",
    "evidence_state",
    "evidence_type",
    "source_url",
    "last_verified_at",
]


def enrich(row):
    out = dict(row)
    for field in ENRICH_FIELDS:
        out.setdefault(field, "")

    # Never turn a derived score into a viability claim. CABE must come from
    # explicit viability evidence or remain unknown.
    out["cabe_status"] = out["cabe_status"] or (
        "reported" if out["cabe"] else "unknown"
    )
    out["rula_status"] = out["rula_status"] or (
        "reported" if out["rula"] else "unknown"
    )
    out["jgb_status"] = out["jgb_status"] or (
        "reported" if out["jgb_level"] else "unknown"
    )

    # A discovered record is not automatically a reported/verified result.
    # Preserve an existing evidence state; otherwise leave it explicitly unknown.
    out["evidence_state"] = out["evidence_state"] or "unknown"
    out["evidence_type"] = out["evidence_type"] or "unknown"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    with open(args.input, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = [enrich(r) for r in reader]
        existing = list(reader.fieldnames or [])
    fields = existing + [f for f in ENRICH_FIELDS if f not in existing]
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} candidates enriched -> {args.out}")


if __name__ == "__main__":
    main()
