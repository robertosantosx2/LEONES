#!/usr/bin/env python3
"""🦁 LEONES · Minimal inference measurement.

ANTES
-----
Responde: «¿qué rendimiento ofrece este endpoint con una petición pequeña y
repetible?». Requiere un servidor local OpenAI-compatible ya iniciado.
No instala software, no descarga modelos y no ejecuta LOTB.

DURANTE
-------
Envía exactamente una petición al endpoint indicado y mide el tiempo total.
Si el servidor informa usage, calcula tokens/s. Los errores se devuelven en
JSON para que la aplicación pueda explicar el siguiente paso.

DESPUÉS
-------
Tokens/s es una medida de inferencia, no una medida de capacidad agentiva.
Un resultado bueno permite continuar a LOTB; uno malo puede indicar que hay
que cambiar modelo, quantización, runtime o configuración.

PRIVACIDAD
----------
La salida JSON no publica URL local ni el prompt utilizado.
"""
from __future__ import annotations
import argparse, json, time, urllib.error, urllib.parse, urllib.request

def main() -> int:
    p = argparse.ArgumentParser(description='Mide una petición local OpenAI-compatible')
    p.add_argument('--url', required=True)
    p.add_argument('--model', required=True)
    p.add_argument('--prompt', default='Explain in one short sentence what a local AI agent is.')
    p.add_argument('--max-tokens', type=int, default=64)
    p.add_argument('--timeout', type=float, default=120)
    p.add_argument('--explain', action='store_true')
    a = p.parse_args()
    parsed = urllib.parse.urlparse(a.url)
    if a.explain:
        print('🦁 LEONES · Medición de inferencia\nSe hará una sola generación pequeña. No es LOTB y no publica nada.\n')
    payload = {'model': a.model, 'messages': [{'role': 'user', 'content': a.prompt}], 'max_tokens': a.max_tokens, 'stream': False}
    req = urllib.request.Request(a.url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'}, method='POST')
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=a.timeout) as response:
            raw = response.read().decode('utf-8')
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        out = {'tool': 'leones-infer', 'tool_version': '1.2', 'status': 'error', 'error_type': type(exc).__name__, 'scope': 'local', 'next_step': 'check-runtime'}
        print(json.dumps(out, indent=2, ensure_ascii=False)); return 2
    elapsed = time.perf_counter() - started
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        out = {'tool': 'leones-infer', 'tool_version': '1.2', 'status': 'error', 'error_type': 'invalid_json_response', 'scope': 'local', 'next_step': 'check-runtime'}
        print(json.dumps(out, indent=2, ensure_ascii=False)); return 2
    usage = data.get('usage', {}) if isinstance(data, dict) else {}
    completion = usage.get('completion_tokens')
    prompt_tokens = usage.get('prompt_tokens')
    speed = round(completion / elapsed, 3) if isinstance(completion, (int, float)) and elapsed > 0 else None
    out = {
        'tool': 'leones-infer',
        'tool_version': '1.2',
        'status': 'ok',
        'model': a.model,
        'scope': 'local',
        'scheme': parsed.scheme,
        'port': parsed.port,
        'elapsed_seconds': round(elapsed, 3),
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion,
        'generation_tokens_per_second': speed,
        'next_step': 'lotb' if speed is not None else 'inspect-runtime-usage',
    }
    print(json.dumps(out, indent=2, ensure_ascii=False)); return 0

if __name__ == '__main__':
    raise SystemExit(main())
