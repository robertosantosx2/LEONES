#!/usr/bin/env python3
"""🦁 LEONES · Router v0.5.

Combina Task Intelligence + Hardware + Model + Atlas + evidencia primaria.
Una ejecución A01 medida puede reforzar o bloquear una ruta concreta. Las
mediciones runtime son evidencia primaria y no deben volver a degradarse a
estimaciones.
"""
from __future__ import annotations
import argparse, json, sys

SAFETY_FACTOR = 1.35


def load_json(path):
    if path == '-': return json.load(sys.stdin)
    with open(path, encoding='utf-8') as f: return json.load(f)


def route(hw, model, task=None, atlas=None, evidence=None):
    h, m = hw.get('hardware', {}), model.get('model', {})
    ram, size = h.get('ram_gb'), m.get('size_bytes')
    fmt = (m.get('format') or '').lower()
    required = None if size is None else size / 1024**3 * SAFETY_FACTOR
    fits = None if ram is None or required is None else required <= ram
    task_name = (task or {}).get('task')
    capabilities = set((task or {}).get('capabilities', []))
    records = (atlas or {}).get('records', [])
    evidence = evidence or {}

    candidates = []
    for r in records:
        if r.get('kind') != 'model': continue
        score = 0
        if r.get('name') == m.get('name'): score += 5
        execution = r.get('execution') or {}
        if fmt and execution.get('format') == m.get('format'): score += 2
        if r.get('evaluation'): score += 1
        ev = r.get('evidence') or {}
        if ev.get('state') in ('reproducible', 'verified'): score += 2
        candidates.append((score, r))
    candidates.sort(key=lambda x: x[0], reverse=True)
    evidence_matches = [r for _, r in candidates if r.get('name') == m.get('name')]

    runtime = 'llama.cpp' if fmt == 'gguf' else None
    decision = 'candidate' if fits is not False else 'reject_memory'
    if task_name == 'vision' and 'vision' not in capabilities:
        decision = 'insufficient_task_capability'

    primary = evidence.get('evidence', {})
    agentic = evidence.get('agentic', {})
    outcome = agentic.get('outcome', {})
    measured = primary.get('evidence_type') in ('measured', 'verified')
    evidence_model = (evidence.get('model') or {}).get('name')
    evidence_runtime = (agentic.get('runtime') or {}).get('name')
    evidence_matches_model = measured and evidence_model and evidence_model == m.get('name')
    runtime_benchmark = evidence.get('runtime_benchmark') or {}
    benchmark_measured = runtime_benchmark.get('status') == 'measured'

    if evidence_matches_model and outcome.get('status') == 'success':
        decision = 'evidence_supported' if decision == 'candidate' else decision
    elif evidence_matches_model and outcome.get('status') in ('failed', 'error'):
        decision = 'evidence_failed'

    reason = 'Heurística basada en memoria, formato, tarea y evidencia Atlas.'
    if evidence_matches_model:
        reason += f" A01 {primary.get('evidence_type')} para este modelo; outcome={outcome.get('status', 'unknown')}"
        if evidence_runtime: reason += f" runtime={evidence_runtime}."
        if benchmark_measured:
            tps = runtime_benchmark.get('tokens_per_second')
            wall = runtime_benchmark.get('wall_seconds')
            reason += f" Benchmark runtime medido: wall={wall}s, tok/s={tps}."
    elif primary:
        reason += ' La evidencia suministrada no corresponde al modelo actual.'
    else:
        reason += ' Sin evidencia primaria de ejecución.'

    return {
        'router_version': '0.5',
        'decision_type': 'heuristic_with_primary_evidence',
        'decision': decision,
        'task': {'name': task_name, 'capabilities': sorted(capabilities)},
        'hardware': {'ram_gb': ram, 'gpu': h.get('gpu'), 'vram_gb': h.get('vram_gb'), 'os': h.get('os')},
        'model': {'name': m.get('name'), 'format': m.get('format'), 'size_bytes': size, 'sha256': m.get('sha256')},
        'atlas': {'records_available': len(records), 'matching_records': len(evidence_matches),
                  'ranked_candidates': [{'name': r.get('name'), 'score': score, 'evidence_state': (r.get('evidence') or {}).get('state')} for score, r in candidates[:5]]},
        'runtime': runtime,
        'primary_evidence': {
            'present': bool(primary), 'type': primary.get('evidence_type'),
            'model_match': bool(evidence_matches_model),
            'runtime_match': bool(evidence_matches_model and (not evidence_runtime or evidence_runtime == runtime)),
            'runtime_benchmark_measured': benchmark_measured,
            'tokens_per_second': runtime_benchmark.get('tokens_per_second'),
            'wall_seconds': runtime_benchmark.get('wall_seconds'),
        },
        'memory_check': {'safety_factor': SAFETY_FACTOR, 'estimated_required_ram_gb': round(required, 2) if required is not None else None, 'fits_heuristically': fits},
        'reason': reason,
        'next_step': 'inference' if benchmark_measured and evidence_matches_model and outcome.get('status') == 'success' else ('runtime_benchmark' if decision == 'evidence_supported' else ('review_constraints' if decision in ('reject_memory', 'insufficient_task_capability', 'evidence_failed') else 'inference'))
    }


def main():
    p = argparse.ArgumentParser(description='LEONES Router v0.5')
    p.add_argument('--hardware', required=True); p.add_argument('--model', required=True)
    p.add_argument('--task'); p.add_argument('--atlas'); p.add_argument('--evidence'); p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        task = load_json(a.task) if a.task else {}
        atlas = load_json(a.atlas) if a.atlas else {}
        evidence = load_json(a.evidence) if a.evidence else {}
        result = route(load_json(a.hardware), load_json(a.model), task, atlas, evidence)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'ERROR: no se pudieron leer las entradas JSON: {exc}', file=sys.stderr); return 2
    if a.json: print(json.dumps(result, indent=2, ensure_ascii=False)); return 0
    print('🦁 LEONES · Router v0.5')
    print(f"Tarea: {result['task']['name'] or 'no definida'}")
    print(f"Decisión: {result['decision']}")
    print(f"Modelo: {result['model']['name'] or 'desconocido'}")
    print(f"Runtime candidato: {result['runtime'] or 'desconocido'}")
    print(f"Evidencia primaria: {result['primary_evidence']['type'] or 'none'}")
    print(f"Siguiente paso: {result['next_step']}")

if __name__ == '__main__': main()
