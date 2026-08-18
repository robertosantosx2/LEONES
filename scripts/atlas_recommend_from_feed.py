#!/usr/bin/env python3
"""Genera recomendaciones Atlas explicables a partir del feed técnico.

Este programa responde a una pregunta concreta: «dado este hardware y este
workload, ¿qué modelos del feed tienen evidencia técnica suficiente para ser
considerados?». No es un benchmark físico y no debe interpretarse como tal.

La documentación para mantenimiento está en:
    docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md

Principios importantes:
- T2/T3 son niveles de evidencia, no una nota de calidad.
- CABE/RULA es una clasificación de velocidad y no sustituye al fit_score.
- El contexto desconocido se conserva como desconocido.
- El precio es evidencia económica independiente.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

try:
    from scripts.classify_performance import classify_measurement
except ModuleNotFoundError:  # ejecución directa
    from classify_performance import classify_measurement

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / 'data/prospection/atlas_feed.csv'
PRICES = ROOT / 'data/hardware/hardware_prices.csv'
OUT = ROOT / 'data/prospection/atlas_recommendations.csv'

FIELDS = [
    'rank', 'model_id', 'model_name', 'variant', 'quantization', 'runtime',
    'hardware_id', 'workload', 'estimated_memory_gb', 'weight_memory_gb',
    'context_tokens', 'context_target_tokens', 'tokens_per_second',
    'performance_class', 'quality_score', 'jgb_level', 'jgb_confidence', 'fit_score', 'confidence',
    'cpu_price_eur', 'cpu_price_source', 'ram_price_eur', 'ram_price_source',
    'gpu_price_eur', 'gpu_price_source', 'hardware_price_eur',
    'price_coverage', 'value_score', 'reason'
]


def num(v):
    """Convierte una celda CSV a float sin confundir vacío con cero."""
    try:
        return float(v) if v not in (None, '') else None
    except (ValueError, TypeError):
        return None


def norm(s):
    """Normaliza texto para comparar identificadores sin depender de mayúsculas."""
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def load_prices():
    """Carga las observaciones económicas disponibles; si no existen, devuelve []."""
    if not PRICES.exists():
        return []
    with PRICES.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def representative(rows):
    """Obtiene la mediana y las fuentes de un conjunto de observaciones."""
    vals = [(num(r.get('price_eur')), r) for r in rows if num(r.get('price_eur')) is not None]
    if not vals:
        return None, ''
    vals.sort(key=lambda x: x[0])
    mid = vals[len(vals) // 2][0]
    sources = ';'.join(sorted({r.get('source', '') for _, r in vals if r.get('source')}))
    return mid, sources


def hardware_price_evidence(hardware_id, ram_gb, vram_gb, prices):
    """Busca precios de CPU, RAM y GPU que correspondan al perfil solicitado.

    El resultado incluye tanto el precio como su fuente y una cobertura `N/3`.
    La cobertura es informativa: nunca convierte datos parciales en un precio
    total de PC.
    """
    hid = norm(hardware_id)
    cpu_rows, ram_rows, gpu_rows = [], [], []

    m = re.search(r'\bi([3579])\b', hid)
    if m:
        cpu_rows = [r for r in prices if r.get('component_type') == 'cpu' and r.get('vendor') == 'intel' and norm(r.get('category', '')) == f'core i{m.group(1)}']
    else:
        m = re.search(r'\bryzen ([3579])\b', hid)
        if m:
            cpu_rows = [r for r in prices if r.get('component_type') == 'cpu' and r.get('vendor') == 'amd' and norm(r.get('category', '')) == f'ryzen {m.group(1)}']

    m = re.search(r'\b(\d+)\s*gb\b', hid)
    cap = int(m.group(1)) if m else int(ram_gb) if ram_gb else None
    ddr = re.search(r'\bddr([45])\b', hid)
    if cap:
        ram_rows = [r for r in prices if r.get('component_type') == 'ram' and r.get('capacity_gb') == str(cap) and (not ddr or norm(r.get('category', '')) == f'ddr{ddr.group(1)}')]

    m = re.search(r'\brtx\s*(\d{3,4}(?:\s*(?:ti|super))?)\b', hid)
    if m:
        gpu_rows = [r for r in prices if r.get('component_type') == 'gpu' and r.get('vendor') == 'nvidia' and norm(r.get('category', '')) == 'rtx ' + m.group(1).lower()]

    cpu, cs = representative(cpu_rows)
    ram, rs = representative(ram_rows)
    gpu, gs = representative(gpu_rows)
    known = [x for x in (cpu, ram, gpu) if x is not None]
    total = sum(known) if known else None
    return cpu, cs, ram, rs, gpu, gs, total, f'{len(known)}/3'


def hardware_compatible(row_hardware, requested):
    """Comprueba compatibilidad declarada sin exigir hardware_id cuando está vacío."""
    rh, req = norm(row_hardware), norm(requested)
    return not rh or rh == req or rh in req


def recommend(rows, prices, workload, hardware, ram, vram, context, min_jgb=None, prefer_jgb=False):
    """Filtra modelos y calcula una puntuación de adecuación explicable.

    El orden lógico es importante: primero se descartan modelos sin evidencia
    técnica suficiente o que no caben en memoria; después se calcula la
    puntuación. CABE/RULA se deriva por separado y nunca se mezcla con fit_score.
    """
    limit = ram + vram
    out = []
    for r in rows:
        if not r.get('model_id') and not r.get('model_name'):
            continue
        if r.get('workload') and r['workload'] != workload:
            continue
        if not hardware_compatible(r.get('hardware_id', ''), hardware):
            continue

        mem = num(r.get('estimated_memory_gb')) or num(r.get('weight_memory_gb'))
        ctx = num(r.get('context_tokens'))
        runtime = (r.get('runtime') or '').strip()
        quant = (r.get('quantization') or '').strip()
        level = (r.get('technical_profile_level') or '').strip()
        weight_observed = num(r.get('weight_memory_gb')) is not None
        if mem is None or not runtime or (not quant and not weight_observed):
            continue
        if level not in ('T2', 'T3') or mem > limit:
            continue

        context_recommended = min(ctx, context) if ctx is not None else None
        jgb = num(r.get('jgb_level'))
        tps = num(r.get('tokens_per_second'))
        quality = num(r.get('quality_score'))
        if min_jgb is not None and (jgb is None or jgb < min_jgb):
            continue

        performance = classify_measurement(tps) if tps is not None else {
            'tokens_per_second': None,
            'performance_class': 'UNKNOWN',
        }

        q = (quality / 100) if quality is not None else 0
        s = min((tps or 0) / 50, 1)
        m = max(0, 1 - mem / max(limit, 1))
        o = (jgb / 5) if jgb is not None else 0
        score = .35 * q + .25 * s + .15 * m + .15 + (.10 * o if prefer_jgb else 0)

        cpu, cs, rp, rs, gpu, gs, total, cov = hardware_price_evidence(hardware, ram, vram, prices)
        value = score / (total / 100) if total else None
        ec = sum(x is not None for x in (mem, ctx, tps, quality, jgb))
        confidence = 'high' if ec == 5 else 'medium' if ec >= 3 else 'low'
        basis = 'observed weight size' if weight_observed else 'estimated memory'
        context_text = f'context supported={int(ctx)}, recommended={int(context_recommended)}' if context_recommended is not None else 'context supported=unknown, recommendation is preliminary'
        reason = [
            f'technical viability {level} supported by {basis}',
            context_text,
            'quality evidence=' + ('available' if quality is not None else 'unknown'),
            'performance evidence=' + ('available' if tps is not None else 'unknown'),
            'performance class=' + performance['performance_class'],
            'JGB=' + (str(int(jgb)) if jgb is not None else 'unknown'),
            f'hardware price coverage={cov}',
        ]
        out.append((score, r, confidence, '; '.join(reason), cpu, cs, rp, rs, gpu, gs, total, cov, value, context_recommended, performance['performance_class']))

    out.sort(key=lambda x: x[0], reverse=True)
    return out


def main():
    """Punto de entrada: lee argumentos, calcula recomendaciones y escribe CSV."""
    p = argparse.ArgumentParser()
    p.add_argument('--workload', required=True)
    p.add_argument('--hardware', required=True)
    p.add_argument('--ram', type=float, required=True)
    p.add_argument('--vram', type=float, default=0)
    p.add_argument('--context', type=int, default=4096)
    p.add_argument('--min-jgb', type=int)
    p.add_argument('--prefer-jgb', action='store_true')
    p.add_argument('--out', default=str(OUT))
    a = p.parse_args()

    with FEED.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    prices = load_prices()
    ranked = recommend(rows, prices, a.workload, a.hardware, a.ram, a.vram, a.context, a.min_jgb, a.prefer_jgb)

    with open(a.out, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for i, x in enumerate(ranked, 1):
            score, r, conf, reason, cpu, cs, rp, rs, gpu, gs, total, cov, value, ctxrec, performance_class = x
            w.writerow({
                'rank': i,
                **{k: r.get(k, '') for k in FIELDS if k in r},
                'performance_class': performance_class,
                'context_target_tokens': int(ctxrec) if ctxrec is not None else '',
                'fit_score': f'{score:.4f}',
                'confidence': conf,
                'cpu_price_eur': f'{cpu:.2f}' if cpu is not None else '',
                'cpu_price_source': cs,
                'ram_price_eur': f'{rp:.2f}' if rp is not None else '',
                'ram_price_source': rs,
                'gpu_price_eur': f'{gpu:.2f}' if gpu is not None else '',
                'gpu_price_source': gs,
                'hardware_price_eur': f'{total:.2f}' if total is not None else '',
                'price_coverage': cov,
                'value_score': f'{value:.6f}' if value is not None else '',
                'reason': reason,
            })

    print(f'{len(ranked)} recommendations -> {a.out}; accepted price observations available={len(prices)}')


if __name__ == '__main__':
    main()
