#!/usr/bin/env python3
"""Merge deterministic recommendation dimensions into an existing CSV.

Existing recommendation columns are preserved. Missing enrichment fields are
added. Unknown values remain unknown; no performance/JGB/RULA inference is made.
"""
from __future__ import annotations
import argparse, csv

ENRICH_FIELDS = [
    'model_id','model_name','hardware_id','fit_score','cabe','cabe_status',
    'rula','rula_status','jgb_level','jgb_status','tokens_per_second',
    'performance_score','economic_score','uncertainty','parameters_total_b',
    'parameters_active_b','quantization','weight_memory_gb','kv_cache_gb',
    'runtime_overhead_gb','memory_margin_gb','runtime','runtime_version',
    'backend','context_length','evidence_state','evidence_type','source_url',
    'last_verified_at'
]

KEYS = ('model_id', 'model_name', 'hardware_id')

def num(v):
    try:
        return float(v) if v not in ('', None) else None
    except (ValueError, TypeError):
        return None

def enrich(row):
    out = dict(row)
    for field in ENRICH_FIELDS:
        out.setdefault(field, '')
    fit = num(out.get('fit_score'))
    if out['cabe'] == '' and fit is not None:
        out['cabe'] = 'true' if fit >= 1 else 'false'
        out['cabe_status'] = 'estimated'
    out['rula_status'] = out['rula_status'] or 'unknown'
    out['jgb_status'] = out['jgb_status'] or ('provisional' if out['jgb_level'] else 'unknown')
    out['evidence_state'] = out['evidence_state'] or 'reported'
    out['evidence_type'] = out['evidence_type'] or 'unknown'
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        rows = [enrich(r) for r in reader]
        existing = list(reader.fieldnames or [])
    fields = existing + [f for f in ENRICH_FIELDS if f not in existing]
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f'{len(rows)} candidates enriched -> {args.out}')

if __name__ == '__main__':
    main()
