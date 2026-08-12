#!/usr/bin/env python3
"""🦁 LEONES · Router v0.1.

Decide una combinación inicial de modelo/runtime a partir de hechos ya
medidos. NO hace benchmark, NO inventa velocidad y NO sustituye a Atlas.

Entrada esperada:
  leones-hardware.py --json
  leones-model.py MODEL --json

La regla v0.1 es deliberadamente transparente: comprueba memoria disponible
frente al tamaño del archivo y propone un runtime únicamente cuando el formato
permite una recomendación explícita. La decisión se etiqueta como heurística.
"""
from __future__ import annotations
import argparse, json, sys

SAFETY_FACTOR = 1.35

def load_json(path):
    if path == '-':
        return json.load(sys.stdin)
    with open(path, encoding='utf-8') as f:
        return json.load(f)

def route(hw, model):
    h = hw.get('hardware', {})
    m = model.get('model', {})
    ram = h.get('ram_gb')
    size = m.get('size_bytes')
    fmt = (m.get('format') or '').lower()
    required = None if size is None else size / 1024**3 * SAFETY_FACTOR
    fits = None if ram is None or required is None else required <= ram
    runtime = None
    reason = 'No hay evidencia suficiente para recomendar un runtime.'
    if fmt == 'gguf':
        runtime = 'llama.cpp'
        reason = 'GGUF permite una recomendación explícita de llama.cpp; el rendimiento debe medirse.'
    elif fmt:
        reason = 'El formato está identificado, pero no se asume compatibilidad de runtime sin evidencia.'
    decision = 'candidate' if fits is not False else 'reject_memory'
    return {
        'router_version': '0.1',
        'decision_type': 'heuristic',
        'decision': decision,
        'hardware': {
            'ram_gb': ram,
            'gpu': h.get('gpu'),
            'vram_gb': h.get('vram_gb'),
            'os': h.get('os'),
        },
        'model': {
            'name': m.get('name'),
            'format': m.get('format'),
            'size_bytes': size,
            'sha256': m.get('sha256'),
        },
        'memory_check': {
            'safety_factor': SAFETY_FACTOR,
            'estimated_required_ram_gb': round(required, 2) if required is not None else None,
            'fits_heuristically': fits,
        },
        'runtime': runtime,
        'reason': reason,
        'next_step': 'inference' if decision == 'candidate' else 'choose_smaller_model',
    }

def main():
    p = argparse.ArgumentParser(description='Router LEONES v0.1: recomendación transparente y heurística')
    p.add_argument('--hardware', required=True, help='JSON generado por leones-hardware.py')
    p.add_argument('--model', required=True, help='JSON generado por leones-model.py')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    try:
        result = route(load_json(a.hardware), load_json(a.model))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'ERROR: no se pudieron leer las entradas JSON: {exc}', file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    print('🦁 LEONES · Router v0.1')
    print(f"Decisión: {result['decision']}")
    print(f"Modelo: {result['model']['name'] or 'desconocido'}")
    print(f"RAM estimada necesaria: {result['memory_check']['estimated_required_ram_gb'] or 'desconocida'} GB")
    print(f"Runtime candidato: {result['runtime'] or 'desconocido'}")
    print(f"Motivo: {result['reason']}")
    print('IMPORTANTE: esta es una heurística; la decisión final requiere una prueba de inferencia.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
