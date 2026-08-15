#!/usr/bin/env python3
"""Enrich Atlas recommendation candidates without inventing measurements.

The script derives only deterministic fields from already observed/source data.
Unknown values remain unknown. JGB is never inferred from performance.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

FIELDS = [
    'model_id','model_name','hardware_id','fit_score','cabe','cabe_status',
    'rula','rula_status','jgb_level','jgb_status','tokens_per_second',
    'performance_score','economic_score','uncertainty','parameters_total_b',
    'parameters_active_b','quantization','weight_memory_gb','kv_cache_gb',
    'runtime_overhead_gb','memory_margin_gb','runtime','runtime_version',
    'backend','context_length','evidence_state','evidence_type','source_url',
    'last_verified_at'
]

def num(v):
    try:
        return float(v) if v not in ('', None) else None
    except (ValueError, TypeError):
        return None

def enrich(row):
    out = {k: row.get(k, '') for k in FIELDS}
    fit = num(row.get('fit_score'))
    if out['cabe'] == '' and fit is not None:
        out['cabe'] = 'true' if fit >= 1 else 'false'
        out['cabe_status'] = 'estimated'
    if out['rula'] == '':
        out['rula_status'] = out['rula_status'] or 'unknown'
    if out['jgb_level'] != '':
        out['jgb_status'] = out['jgb_status'] or 'provisional'
    else:
        out['jgb_status'] = out['jgb_status'] or 'unknown'
    if out['evidence_state'] == '':
        out['evidence_state'] = 'reported'
    if out['evidence_type'] == '':
        out['evidence_type'] = 'unknown'
    # Never derive performance from JGB, and never derive RULA from CABE.
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    with open(args.input, encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    with open(args.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(enrich(r) for r in rows)
    print(f'{len(rows)} candidates enriched -> {args.out}')

if __name__ == '__main__':
    main()
