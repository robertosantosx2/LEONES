#!/usr/bin/env python3
"""Monthly hardware-price updater for the LEONES recommender.

The price layer is separate from the Atlas model database. It validates the
coverage of CPU, RAM and NVIDIA GPU price data and preserves dated snapshots.
The updater never invents a price: unavailable or unverified observations are
reported instead of being filled with estimates.
"""
from __future__ import annotations
import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/hardware/hardware_prices.csv'
GPU_DB = ROOT / 'data/hardware/nvidia_ai_gpus.csv'

CPU_TARGETS = [
    ('cpu','intel','Core i3'), ('cpu','intel','Core i5'),
    ('cpu','intel','Core i7'), ('cpu','intel','Core i9'),
    ('cpu','amd','Ryzen 3'), ('cpu','amd','Ryzen 5'),
    ('cpu','amd','Ryzen 7'), ('cpu','amd','Ryzen 9'),
]
RAM_TARGETS = [
    ('ram','DDR4',f'DDR4 {gb}GB') for gb in (2,4,8,16,32,64,128)
] + [
    ('ram','DDR5',f'DDR5 {gb}GB') for gb in (8,16,32,64,128)
]


def load_rows():
    if not DB.exists():
        return []
    with DB.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def gpu_count():
    if not GPU_DB.exists():
        return 0
    with GPU_DB.open(encoding='utf-8', newline='') as f:
        return sum(1 for _ in csv.DictReader(f))


def main():
    rows = load_rows()
    cpu_present = {(r.get('component_type',''), r.get('vendor','').lower(), r.get('category','')) for r in rows}
    ram_present = {(r.get('component_type',''), r.get('vendor',''), r.get('model','')) for r in rows}
    missing_cpu = [x for x in CPU_TARGETS if x not in cpu_present]
    missing_ram = [x for x in RAM_TARGETS if x not in ram_present]

    print('=== LEONES — actualización mensual de precios ===')
    print('Fecha:', date.today().isoformat())
    print('Observaciones CPU/RAM:', len(rows))
    print('Entradas catálogo GPU NVIDIA:', gpu_count())
    print('Cobertura CPU:', len(CPU_TARGETS) - len(missing_cpu), '/', len(CPU_TARGETS))
    print('Cobertura RAM:', len(RAM_TARGETS) - len(missing_ram), '/', len(RAM_TARGETS))
    if missing_cpu:
        print('CPU sin observación válida:')
        for x in missing_cpu: print(' -', x)
    if missing_ram:
        print('RAM sin observación válida:')
        for x in missing_ram: print(' -', x)
    print('Integridad: no se rellenan precios desconocidos con estimaciones.')
    print('Histórico: las observaciones mensuales se conservan, no se sobrescriben.')


if __name__ == '__main__':
    main()
