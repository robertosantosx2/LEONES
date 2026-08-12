#!/usr/bin/env python3
"""🦁 LEONES · Router v0.3.

Combina Task Intelligence + Hardware + Model + Atlas.
La decisión sigue siendo heurística hasta disponer de evidencia reproducible.
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

    candidates = []
    for r in records:
        if r.get('kind') != 'model':
            continue
        score = 0
        if r.get('name') == m.get('name'): score += 5
        execution = r.get('execution') or {}
        if fmt and execution.get('format') == m.get('format'): score += 2
        evals = r.get('evaluation') or []
        if evals: score += 1
        evidence = r.get('evidence') or {}
        if evidence.get('state') in ('reproducible', 'verified'): score += 2
        candidates.append((score, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    evidence_matches = [r for _, r in candidates if r.get('name') == m.get('name')]

    runtime = 'llama.cpp' if fmt == 'gguf' else None
    decision = 'candidate' if fits is not False else 'reject_memory'
    if task_name == 'vision' and 'vision' not in capabilities:
        decision = 'insufficient_task_capability'

    reason = 'Heurística basada en memoria, formato, tarea y evidencia Atlas; requiere inferencia/LOTB.'
    if evidence_matches:
        reason += ' Existe evidencia Atlas para este modelo.'
    elif records:
        reason += ' No existe coincidencia Atlas para este modelo.'
    else:
        reason += ' Atlas no contiene registros todavía.'

    return {
        'router_version': '0.3',
        'decision_type': 'heuristic',
        'decision': decision,
        'task': {'name': task_name, 'capabilities': sorted(capabilities)},
        'hardware': {'ram_gb': ram, 'gpu': h.get('gpu'), 'vram_gb': h.get('vram_gb'), 'os': h.get('os')},
        'model': {'name': m.get('name'), 'format': m.get('format'), 'size_bytes': size, 'sha256': m.get('sha256')},
        'atlas': {
            'records_available': len(records),
            'matching_records': len(evidence_matches),
            'ranked_candidates': [
                {'name': r.get('name'), 'score': score, 'evidence_state': (r.get('evidence') or {}).get('state')}
                for score, r in candidates[:5]
            ]
        },
        'memory_check': {'safety_factor': SAFETY_FACTOR, 'estimated_required_ram_gb': round(required, 2) if required is not None else None, 'fits_heuristically': fits},
        'runtime': runtime,
        'reason': reason,
        'next_step': 'inference' if decision == 'candidate' else 'review_constraints'
    }

def main():
    p = argparse.ArgumentParser(description='LEONES Router v0.3')
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
    print('🦁 LEONES · Router v0.3')
    print(f"Tarea: {result['task']['name'] or 'no definida'}")
    print(f"Decisión: {result['decision']}")
    print(f"Modelo: {result['model']['name'] or 'desconocido'}")
    print(f"Runtime candidato: {result['runtime'] or 'desconocido'}")
    print(f"Atlas: {result['atlas']['matching_records']} coincidencias; {len(result['atlas']['ranked_candidates'])} candidatos")
    print('IMPORTANTE: decisión heurística; requiere inferencia y LOTB.')

if __name__ == '__main__': main()
