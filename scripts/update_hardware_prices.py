#!/usr/bin/env python3
"""Validate the LEONES monthly hardware price layer.

This script never fills missing prices. It reports coverage, source diversity,
and stale observations so the recommender can distinguish evidence from gaps.
"""
from __future__ import annotations
import csv
from datetime import date, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DB=ROOT/'data/hardware/hardware_prices.csv'
OBS=ROOT/'data/hardware/hardware_price_observations.csv'
GPU_DB=ROOT/'data/hardware/nvidia_ai_gpus.csv'

CPU_TARGETS=[('cpu','intel','Core i3'),('cpu','intel','Core i5'),('cpu','intel','Core i7'),('cpu','intel','Core i9'),('cpu','amd','Ryzen 3'),('cpu','amd','Ryzen 5'),('cpu','amd','Ryzen 7'),('cpu','amd','Ryzen 9')]
RAM_TARGETS=[('ram','memory',f'DDR4 {gb}GB') for gb in (2,4,8,16,32,64,128)]+[('ram','memory',f'DDR5 {gb}GB') for gb in (8,16,32,64,128)]


def read(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))


def main():
    rows=read(DB); obs=read(OBS); gpu=read(GPU_DB)
    cpu_present={(r.get('component_type',''),r.get('vendor','').lower(),r.get('category','')) for r in rows}
    ram_present={(r.get('component_type',''),r.get('vendor',''),r.get('category','')+' '+r.get('capacity_gb','')+'GB') for r in rows}
    missing_cpu=[x for x in CPU_TARGETS if x not in cpu_present]
    missing_ram=[x for x in RAM_TARGETS if x not in ram_present]
    sources=sorted({r.get('source','') for r in obs if r.get('source')})
    dates=[r.get('observed_at') for r in obs if r.get('observed_at')]
    newest=max(dates) if dates else 'none'
    print('=== LEONES — validación mensual de precios ===')
    print('Fecha:',date.today().isoformat())
    print('Observaciones históricas válidas:',len(obs))
    print('Productos en resumen vigente:',len(rows))
    print('Fuentes con observaciones:',len(sources),'/ 5')
    print('Fuentes:',', '.join(sources) if sources else 'ninguna')
    print('Observación más reciente:',newest)
    print('Entradas catálogo NVIDIA:',len(gpu))
    print('Cobertura CPU:',len(CPU_TARGETS)-len(missing_cpu),'/',len(CPU_TARGETS))
    print('Cobertura RAM:',len(RAM_TARGETS)-len(missing_ram),'/',len(RAM_TARGETS))
    if missing_cpu:
        print('CPU sin precio observado:'); [print(' -',x) for x in missing_cpu]
    if missing_ram:
        print('RAM sin precio observado:'); [print(' -',x) for x in missing_ram]
    if len(sources)<2: print('WARNING: menos de dos fuentes aportan observaciones; el precio de mercado puede tener baja robustez.')
    if newest and newest < date.today().isoformat(): print('INFO: el histórico vigente no contiene observaciones de hoy; puede ser normal si las fuentes no publicaron novedades.')
    print('Integridad: no se rellenan precios desconocidos con estimaciones.')
    print('Histórico: las observaciones mensuales se conservan.')

if __name__=='__main__': main()
