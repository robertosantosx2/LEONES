#!/usr/bin/env python3
"""Monthly hardware-price updater.

This bot intentionally stores observations separately from Atlas model data.
It is conservative: it records source/date/price and does not invent missing
prices. Retail sources can change markup and availability, so observations are
kept as dated snapshots rather than overwriting history.
"""
from __future__ import annotations
import csv
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/hardware/hardware_prices.csv'

# Seed/validation targets. The monthly job can be extended with additional
# retailers or APIs without changing the Atlas schema.
TARGETS=[
 ('cpu','intel','Core i3'),('cpu','intel','Core i5'),('cpu','intel','Core i7'),('cpu','intel','Core i9'),
 ('cpu','amd','Ryzen 3'),('cpu','amd','Ryzen 5'),('cpu','amd','Ryzen 7'),('cpu','amd','Ryzen 9'),
 ('ram','system','DDR4 8GB'),('ram','system','DDR4 16GB'),('ram','system','DDR4 32GB'),('ram','system','DDR4 64GB'),('ram','system','DDR4 128GB'),
 ('ram','system','DDR5 8GB'),('ram','system','DDR5 16GB'),('ram','system','DDR5 32GB'),('ram','system','DDR5 64GB'),('ram','system','DDR5 128GB'),
]

# The script is deliberately source-neutral. It validates that the database
# contains every target and reports missing observations; source adapters can
# populate prices from permitted retailer/API feeds.
def main():
    rows=list(csv.DictReader(DB.open(encoding='utf-8')))
    present={(r['component_type'],r['vendor'],r['category'] if r['component_type']=='cpu' else r['model']) for r in rows}
    missing=[t for t in TARGETS if t not in present]
    print(f'Hardware price database: {len(rows)} observations/targets')
    if missing:
        print('Missing targets:')
        for x in missing: print(' -',x)
    print('Monthly refresh date:', date.today().isoformat())

if __name__=='__main__': main()
