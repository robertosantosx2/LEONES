#!/usr/bin/env python3
"""🦁 LEONES · Router v0.2.

Combina Task Intelligence + Hardware + Model + Atlas cuando hay evidencia.
Nunca inventa rendimiento ni convierte una heurística en benchmark.
"""
from __future__ import annotations
import argparse, json, sys

SAFETY_FACTOR = 1.35

def load_json(path):
    if path == '-': return json.load(sys.stdin)
    with open(path, encoding='utf-8') as f: return json.load(f)

def route(hw, model, task=None, atlas=None):
    h, m = hw.get('hardware', {}), model.get('model', {})
    ram, size = h.get('ram_gb'), m.get('size_bytes')
    fmt = (m.get('format') or '').lower()
    required = None if size is None else size / 1024**3 * SAFETY_FACTOR
    fits = None if ram is None or required is None else required <= ram
    task_name = (task or {}).get('task')
    capabilities = set((task or {}).get('capabilities', []))
    records = (atlas or {}).get('records', [])
    evidence_matches = []
    for r in records:
        if r.get('kind') == 'model' and r.get('name') == m.get('name'):
            evidence_matches.append(r)
    runtime = 'llama.cpp' if fmt == 'gguf' else None
    decision = 'candidate' if fits is not False else 'reject_memory'
    if task_name == 'vision' and 'vision' not in capabilities:
        decision = 'insufficient_task_capability'
    reason = 'Heurística basada en memoria y formato; requiere inferencia/LOTB.'
    if evidence_matches:
        reason += ' Existe evidencia Atlas para este modelo.'
    elif records:
        reason += ' No existe coincidencia Atlas para este modelo.'
    return {
        'router_version': '0.2', 'decision_type': 'heuristic', 'decision': decision,
        'task': {'name': task_name, 'capabilities': sorted(capabilities)},
        'hardware': {'ram_gb': ram, 'gpu': h.get('gpu'), 'vram_gb': h.get('vram_gb'), 'os': h.get('os')},
        'model': {'name': m.get('name'), 'format': m.get('format'), 'size_bytes': size, 'sha256': m.get('sha256')},
        'atlas': {'records_available': len(records), 'matching_records': len(evidence_matches)},
        'memory_check': {'safety_factor': SAFETY_FACTOR, 'estimated_required_ram_gb': round(required, 2) if required is not None else None, 'fits_heuristically': fits},
        'runtime': runtime, 'reason': reason,
        'next_step': 'inference' if decision == 'candidate' else 'review_constraints'
    }

def main():
    p = argparse.ArgumentParser(description='LEONES Router v0.2')
    p.add_argument('--hardware', required=True); p.add_argument('--model', required=True)
    p.add_argument('--task'); p.add_argument('--atlas'); p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        task = load_json(a.task) if a.task else {}
        atlas = load_json(a.atlas) if a.atlas else {}
        result = route(load_json(a.hardware), load_json(a.model), task, atlas)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'ERROR: no se pudieron leer las entradas JSON: {exc}', file=sys.stderr); return 2
    if a.json: print(json.dumps(result, indent=2, ensure_ascii=False)); return 0
    print('🦁 LEONES · Router v0.2')
    print(f"Tarea: {result['task']['name'] or 'no definida'}")
    print(f"Decisión: {result['decision']}")
    print(f"Modelo: {result['model']['name'] or 'desconocido'}")
    print(f"Runtime candidato: {result['runtime'] or 'desconocido'}")
    print(f"Atlas: {result['atlas']['matching_records']} coincidencias")
    print('IMPORTANTE: decisión heurística; requiere inferencia y LOTB.')

if __name__ == '__main__': main()
