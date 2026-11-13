#!/usr/bin/env python3
"""Run the fixed battery and sample host resources separately for every request."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import pathlib
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from resource_monitor import RequestSampler
from moe_runtime_probe import RuntimeProbe

ARITHMETIC = "¿Cuánto es 17 por 23? Responde brevemente."
TWO_SUM = ("Escribe una función Python two_sum(nums, target) que devuelva los índices de dos "
"elementos distintos cuya suma sea target. Requisitos: complejidad O(n), admitir números "
"negativos y duplicados, no reutilizar el mismo índice y devolver None si no existe solución. "
"Explica brevemente el algoritmo y proporciona tres pruebas, incluyendo un duplicado y un "
"número negativo. Presenta código completo.")
BINARY_SEARCH = """Analiza este código Python de búsqueda binaria. Tiene un error lógico que puede provocar un bucle infinito. Identifica exactamente el error, explica por qué ocurre, proporciona una versión corregida completa y añade pruebas para un elemento presente, uno ausente, una lista vacía y una lista de un elemento. El contrato es: lista ordenada ascendentemente de enteros, devolver el índice si existe y -1 si no existe. Código defectuoso:
def binary_search(nums, target):
    left, right = 0, len(nums) - 1
    while left <= right:
        mid = (left + right) // 2
        if nums[mid] == target:
            return mid
        elif nums[mid] < target:
            left = mid
        else:
            right = mid - 1
    return -1"""

CASES = [
    ("arithmetic", ARITHMETIC, 64, 256),
    ("arithmetic", ARITHMETIC, 128, 384),
    ("arithmetic", ARITHMETIC, 256, 512),
    ("two_sum", TWO_SUM, 128, 512),
    ("two_sum", TWO_SUM, 128, 768),
    ("two_sum", TWO_SUM, 256, 1024),
    ("two_sum", TWO_SUM, 128, 1536),
    ("two_sum", TWO_SUM, 256, 1536),
    ("binary_search", BINARY_SEARCH, 128, 1536),
    ("binary_search", BINARY_SEARCH, 256, 1536),
]

def get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def post_json(url, payload, timeout):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18086")
    parser.add_argument("--model", required=True)
    parser.add_argument("--engine", required=True)
    parser.add_argument("--mode", required=True, choices=["same-engine-new-model", "same-model-new-engine"])
    parser.add_argument("--model-path", default="")
    parser.add_argument("--output", default="")
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--monitor-interval", type=float, default=1.0)
    parser.add_argument("--server-pid", type=int, default=None)
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    parsed = urlparse(base)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
    out = pathlib.Path(args.output or ("tandem-battery-" + stamp))
    out.mkdir(parents=True, exist_ok=False)
    (out / "responses").mkdir()
    (out / "resources").mkdir()

    manifest = {
        "started_at": dt.datetime.now().astimezone().isoformat(),
        "mode": args.mode,
        "engine": args.engine,
        "model": args.model,
        "model_path_or_id": args.model_path,
        "base_url": base,
        "temperature": 0,
        "stream": False,
        "thinking": True,
        "reasoning_format": "deepseek",
        "cases": [{"task": task, "budget": budget, "max_tokens": maximum}
                  for task, _, budget, maximum in CASES],
        "note": "Client does not change server configuration.",
        "resource_monitor": {
            "interval_seconds": args.monitor_interval,
            "server_pid_argument": args.server_pid,
            "metrics": "resource_monitor.py plus moe_runtime_probe.py: Linux /proc, PSI, process I/O/scheduler, CPU frequency, NVIDIA utilization/VRAM/PCIe throughput; PSI and PCIe counters are host/device-wide",
        },
    }
    for endpoint in ("/health", "/props"):
        try:
            manifest[endpoint[1:]] = get_json(base + endpoint)
        except Exception as error:
            manifest[endpoint[1:]] = {"capture_error": str(error)}

    cases = CASES[:args.limit] if args.limit else CASES
    with (out / "summary.jsonl").open("w", encoding="utf-8") as summary:
        for index, (task, prompt, budget, maximum) in enumerate(cases, 1):
            payload = {
                "model": args.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "max_tokens": maximum,
                "reasoning_format": "deepseek",
                "reasoning_budget_tokens": budget,
                "chat_template_kwargs": {"enable_thinking": True},
                "stream": False,
            }
            record = {
                "index": index,
                "task": task,
                "budget": budget,
                "max_tokens": maximum,
                "started_at": dt.datetime.now().astimezone().isoformat(),
                "request": payload,
            }
            sampler = RequestSampler(
                out / "resources",
                f"case-{index:02d}",
                port,
                args.server_pid,
                args.monitor_interval,
                args.model_path,
            )
            sampler.start()
            runtime_probe = RuntimeProbe(out / "resources", f"case-{index:02d}", sampler.pid, args.monitor_interval)
            runtime_probe.start()
            try:
                result = post_json(base + "/v1/chat/completions", payload, args.timeout)
                record["response"] = result
                choice = (result.get("choices") or [{}])[0]
                message = choice.get("message") or {}
                timing = result.get("timings") or {}
                usage = result.get("usage") or {}
                record["metrics"] = {
                    "id": result.get("id"),
                    "finish_reason": choice.get("finish_reason"),
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                    "prompt_ms": timing.get("prompt_ms"),
                    "predicted_ms": timing.get("predicted_ms"),
                    "prompt_tokens_per_second": timing.get("prompt_per_second"),
                    "generation_tokens_per_second": timing.get("predicted_per_second"),
                    "content_chars": len(message.get("content") or ""),
                    "reasoning_chars": len(message.get("reasoning_content") or ""),
                }
            except urllib.error.HTTPError as error:
                record["error"] = {"http_status": error.code, "body": error.read().decode(errors="replace")}
            except Exception as error:
                record["error"] = {"type": type(error).__name__, "message": str(error)}
            finally:
                try:
                    record["resource_metrics"] = sampler.finish()
                except Exception as error:
                    record["resource_monitor_error"] = str(error)
                try:
                    record["moe_runtime_metrics"] = runtime_probe.finish()
                except Exception as error:
                    record["moe_runtime_probe_error"] = str(error)

            record["finished_at"] = dt.datetime.now().astimezone().isoformat()
            filename = f"{index:02d}-{task}-budget{budget}-max{maximum}.json"
            (out / "responses" / filename).write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            row = dict(record.get("metrics", record.get("error", {})))
            row.update({
                "task": task,
                "budget": budget,
                "max_tokens": maximum,
                "resource_metrics": record.get("resource_metrics"),
                "moe_runtime_metrics": record.get("moe_runtime_metrics"),
                "resource_monitor_error": record.get("resource_monitor_error"),
                "moe_runtime_probe_error": record.get("moe_runtime_probe_error"),
            })
            summary.write(json.dumps(row, ensure_ascii=False) + "\n")
            summary.flush()
            print(f"[{index}/{len(cases)}] {task} budget={budget} max={maximum}: {row}", flush=True)
            if index < len(cases) and args.pause:
                time.sleep(args.pause)

    manifest["finished_at"] = dt.datetime.now().astimezone().isoformat()
    (out / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("Results:", out.resolve())

if __name__ == "__main__":
    main()
