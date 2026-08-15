#!/usr/bin/env python3
"""Quality gate for the LEONES hardware price layer.

Keeps the monthly observation ledger intact, but excludes observations that
are clearly not individual components from the current/market summaries.
No price is invented or silently repaired.
"""
from __future__ import annotations
import csv
import re
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT / 'data/hardware/hardware_price_observations.csv'
SUMMARY = ROOT / 'data/hardware/hardware_prices.csv'
MARKET = ROOT / 'data/hardware/hardware_price_market_summary.csv'
QUALITY = ROOT / 'data/hardware/hardware_price_quality.csv'

FIELDS = ['observed_at','component_type','vendor','category','model','capacity_gb','vram_gb','price_eur','price_type','market','currency','source','source_url','notes']

COMPLETE_SYSTEM = re.compile(r'\b(?:pc|ordenador|computador|desktop|port[aá]til|laptop|notebook|barebone|all[ -]?in[ -]?one)\b', re.I)
CPU_WORDS = re.compile(r'\b(?:core\s+i[3579]|ryzen\s+[3579])\b', re.I)
GPU_WORDS = re.compile(r'\brtx\s*\d{3,4}(?:\s*(?:ti|super))?\b', re.I)
RAM_WORDS = re.compile(r'\bddr[45]\b', re.I)


def read(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def assess(row):
    name = (row.get('model') or '').strip()
    kind = (row.get('component_type') or '').lower()
    score = 100
    reasons = []
    if not name or len(name) > 180:
        score -= 100; reasons.append('invalid_name')
    if COMPLETE_SYSTEM.search(name):
        score -= 80; reasons.append('complete_system_or_laptop')
    if kind == 'cpu' and not CPU_WORDS.search(name):
        score -= 60; reasons.append('cpu_model_not_detected')
    if kind == 'gpu' and (not GPU_WORDS.search(name) or 'nvidia' not in (row.get('vendor') or '').lower()):
        score -= 60; reasons.append('gpu_model_not_detected')
    if kind == 'ram' and not RAM_WORDS.search(name):
        score -= 60; reasons.append('ram_model_not_detected')
    try:
        price = float(str(row.get('price_eur','')).replace(',','.'))
    except ValueError:
        price = 0
    if not 5 <= price <= 10000:
        score -= 100; reasons.append('price_out_of_range')
    status = 'accepted' if score >= 70 else 'rejected'
    return score, status, ';'.join(reasons) or 'ok'


def main():
    rows = read(OBS)
    accepted = []
    quality_rows = []
    for row in rows:
        score, status, reason = assess(row)
        q = dict(row)
        q['quality_score'] = str(score)
        q['quality_status'] = status
        q['quality_reason'] = reason
        quality_rows.append(q)
        if status == 'accepted':
            accepted.append(row)

    with QUALITY.open('w', encoding='utf-8', newline='') as f:
        fields = FIELDS + ['quality_score','quality_status','quality_reason']
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(quality_rows)

    latest = {}
    for row in accepted:
        key = (row.get('component_type',''), row.get('vendor',''), row.get('category',''), row.get('model',''), row.get('capacity_gb',''), row.get('vram_gb',''))
        latest[key] = row
    summary_fields = ['price_id','component_type','vendor','category','model','capacity_gb','price_eur','price_type','market','currency','source','observed_at','valid_until','notes']
    with SUMMARY.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=summary_fields); w.writeheader()
        for r in latest.values():
            w.writerow({
                'price_id': f"{r.get('component_type')}|{r.get('vendor')}|{r.get('model')}|{r.get('capacity_gb')}|{r.get('vram_gb')}",
                'component_type': r.get('component_type',''), 'vendor': r.get('vendor',''), 'category': r.get('category',''),
                'model': r.get('model',''), 'capacity_gb': r.get('capacity_gb',''), 'price_eur': r.get('price_eur',''),
                'price_type': 'observed', 'market': r.get('market','Spain'), 'currency': r.get('currency','EUR'),
                'source': r.get('source',''), 'observed_at': r.get('observed_at',''), 'valid_until': '', 'notes': r.get('notes','')
            })

    groups = {}
    for r in accepted:
        key = (r.get('component_type',''), r.get('vendor',''), r.get('category',''), r.get('model',''), r.get('capacity_gb',''), r.get('vram_gb',''))
        groups.setdefault(key, []).append(r)
    market_fields = ['component_type','vendor','category','model','capacity_gb','vram_gb','source_count','sources','min_price_eur','median_price_eur','max_price_eur','latest_observed_at']
    with MARKET.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=market_fields); w.writeheader()
        for key, values in groups.items():
            prices = sorted(float(v['price_eur']) for v in values)
            w.writerow(dict(zip(market_fields, [
                *key, len(set(v.get('source','') for v in values)), ';'.join(sorted(set(v.get('source','') for v in values))),
                f'{min(prices):.2f}', f'{median(prices):.2f}', f'{max(prices):.2f}', max(v.get('observed_at','') for v in values)
            ])))

    rejected = len(rows) - len(accepted)
    print(f'QUALITY: accepted={len(accepted)} rejected={rejected} total={len(rows)}')
    if rejected:
        print('QUALITY: rejected observations remain in the immutable monthly ledger; they are excluded from summaries/recommender input.')


if __name__ == '__main__':
    main()
