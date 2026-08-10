#!/usr/bin/env python3
"""LOTB agentic standard test runner.

Runs a small, deterministic set of local agentic smoke tests against an
OpenAI-compatible local endpoint. It does not require a specific harness.
The tests are designed to simplify first-pass evaluation; full LOTB
verification may use the harness-native implementation afterwards.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BASE = "http://127.0.0.1:8080/v1"

TESTS = [
    {
        "id": "B01",
        "name": "memoria/localidad",
        "prompt": "Recuerda exactamente esta cadena: LOTB-B01-7F3K9. Responde solo con la cadena.",
        "check": lambda text: "LOTB-B01-7F3K9" in text,
    },
    {
        "id": "B02",
        "name": "operación sobre archivos",
        "prompt": "Necesito preparar una tarea local. Indica exactamente qué archivo crear para esta prueba: results/lotb/B02.txt. Responde solo con esa ruta.",
        "check": lambda text: "results/lotb/B02.txt" in text,
    },
    {
        "id": "B03",
        "name": "tarea multietapa",
        "prompt": "Resuelve en este orden: 1) calcula 17+25; 2) multiplica el resultado por 3; 3) responde solo con el número final.",
        "check": lambda text: bool(re.search(r"\b126\b", text)),
    },
    {
        "id": "B04",
        "name": "recuperación ante fallo",
        "prompt": "La primera instrucción de una tarea ha fallado. Sin ejecutar nada, explica en una frase cuál debe ser el siguiente paso: comprobar el error, corregirlo y reintentar. Responde solo con una frase.",
        "check": lambda text: any(x in text.lower() for x in ("comprobar", "error")) and any(x in text.lower() for x in ("reintentar", "corregir")),
    },
    {
        "id": "B05",
        "name": "coding local",
        "prompt": "Escribe una función Python llamada suma(a, b) que devuelva a+b. Responde únicamente con el código de la función.",
        "check": lambda text: "def suma" in text and "return a + b" in text.replace(" ", "") or ("def suma" in text and "return a+b" in text.replace(" ", "")),
    },
]


def post_json(url, payload, timeout):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def get_json(url, timeout):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def ask(base, model, prompt, timeout, max_tokens):
    started = time.perf_counter()
    result = post_json(
        base.rstrip("/") + "/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": max_tokens,
        },
        timeout,
    )
    elapsed = time.perf_counter() - started
    choice = result.get("choices", [{}])[0]
    text = choice.get("message", {}).get("content", "") or ""
    usage = result.get("usage", {}) or {}
    return text, elapsed, usage


def main():
    parser = argparse.ArgumentParser(description="Run the standard LOTB agentic smoke tests.")
    parser.add_argument("--base-url", default=os.getenv("LOAS_BASE_URL", DEFAULT_BASE))
    parser.add_argument("--model", default=os.getenv("LOAS_MODEL", "local-model"))
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--output", default="results/lotb/latest.json")
    args = parser.parse_args()

    print("LOAS LOTB agentic smoke test")
    print(f"Endpoint: {args.base_url}")
    print(f"Model:    {args.model}")

    try:
        models = get_json(args.base_url.rstrip("/") + "/models", args.timeout)
        print("Server:   OK")
        if args.model == "local-model" and models.get("data"):
            args.model = models["data"][0].get("id", args.model)
            print(f"Model:    {args.model} (auto-detected)")
    except Exception as exc:
        print(f"ERROR: local OpenAI-compatible server unavailable: {exc}", file=sys.stderr)
        return 2

    results = []
    for test in TESTS:
        print(f"\n{test['id']} — {test['name']}")
        try:
            text, elapsed, usage = ask(args.base_url, args.model, test["prompt"], args.timeout, args.max_tokens)
            passed = bool(test["check"](text))
            result = {
                "id": test["id"],
                "name": test["name"],
                "passed": passed,
                "elapsed_s": round(elapsed, 3),
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "response": text,
            }
            print(f"  {'PASS' if passed else 'FAIL'}  {elapsed:.2f}s")
        except Exception as exc:
            result = {"id": test["id"], "name": test["name"], "passed": False, "error": str(exc)}
            print(f"  ERROR {exc}")
        results.append(result)

    passed = sum(1 for r in results if r.get("passed"))
    report = {
        "protocol": "LOTB-agentic-smoke-v0.1",
        "endpoint": args.base_url,
        "model": args.model,
        "tests": results,
        "summary": {"passed": passed, "total": len(results), "all_passed": passed == len(results)},
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResult: {passed}/{len(results)} tests passed")
    print(f"Saved:  {output}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
