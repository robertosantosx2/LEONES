#!/usr/bin/env python3
"""🦁 LEONES Runtime v1.3 — detecta y describe un runtime local.

No instala software, descarga modelos ni envía prompts a Internet.
Puede consultar endpoints locales de OpenAI-compatible y Ollama.
"""
from __future__ import annotations
import argparse, json, time, urllib.error, urllib.parse, urllib.request

def get_json(url: str, timeout: float):
    req = urllib.request.Request(url, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read(65536)
        return r.status, json.loads(raw.decode('utf-8')) if raw else {}

def inspect(url: str, timeout: float) -> dict:
    started = time.perf_counter()
    parsed = urllib.parse.urlparse(url)
    try:
        status, payload = get_json(url, timeout)
        data = {'reachable': True, 'http_status': status, 'elapsed_seconds': round(time.perf_counter()-started, 3), 'scope': 'local', 'scheme': parsed.scheme, 'port': parsed.port}
        if '/v1/models' in parsed.path:
            data['protocol'] = 'openai_compatible'
            data['models'] = [x.get('id') for x in payload.get('data', []) if isinstance(x, dict) and x.get('id')]
        elif '/api/tags' in parsed.path:
            data['protocol'] = 'ollama'
            data['models'] = [x.get('name') for x in payload.get('models', []) if isinstance(x, dict) and x.get('name')]
        else:
            data['protocol'] = 'unknown'
        return data
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {'reachable': False, 'error_type': type(exc).__name__, 'elapsed_seconds': round(time.perf_counter()-started, 3), 'scope': 'local', 'scheme': parsed.scheme, 'port': parsed.port}

def main() -> int:
    p = argparse.ArgumentParser(description='Describe un runtime local sin instalar ni ejecutar modelos')
    p.add_argument('--url', action='append', help='Endpoint local; puede repetirse')
    p.add_argument('--timeout', type=float, default=5)
    a = p.parse_args()
    urls = a.url or ['http://127.0.0.1:8080/v1/models', 'http://127.0.0.1:11434/api/tags']
    results = [inspect(u, a.timeout) for u in urls]
    reachable = [r for r in results if r['reachable']]
    out = {'schema_version': '1.2', 'tool': 'leones-runtime', 'tool_version': '1.3', 'status': 'ok' if reachable else 'no_runtime', 'endpoints': results, 'next_step': 'infer' if reachable else 'runtime setup'}
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if reachable else 2

if __name__ == '__main__': raise SystemExit(main())
