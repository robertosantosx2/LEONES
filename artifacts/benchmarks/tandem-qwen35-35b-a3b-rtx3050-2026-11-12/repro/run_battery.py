#!/usr/bin/env python3
"""Run a fixed reasoning/code/debug battery against an OpenAI-compatible server.
Never starts, stops, or reconfigures the inference server. Python 3.10+, stdlib only.
"""
from __future__ import annotations
import argparse, datetime as dt, json, pathlib, time, urllib.error, urllib.request\nfrom urllib.parse import urlparse\nfrom resource_monitor import RequestSampler

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

# Distinct parameter combinations observed in the original campaign; duplicate IDs are excluded.
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
    req = urllib.request.Request(url, headers={"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def post_json(url, payload, timeout):
    req = urllib.request.Request(url, data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type":"application/json","Accept":"application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default="http://127.0.0.1:18086")
    p.add_argument("--model", required=True)
    p.add_argument("--engine", required=True)
    p.add_argument("--mode", required=True, choices=["same-engine-new-model","same-model-new-engine"])
    p.add_argument("--model-path", default="")
    p.add_argument("--output", default="")
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--pause", type=float, default=1.0)
    p.add_argument("--limit", type=int, default=0)\n    p.add_argument("--monitor-interval", type=float, default=1.0, help="Resource sampling interval in seconds")\n    p.add_argument("--server-pid", type=int, default=None, help="Explicit llama-server PID; auto-detected by API port if omitted")
    a = p.parse_args()
    base = a.base_url.rstrip("/")
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d-%H%M%S%z")
    out = pathlib.Path(a.output or ("tandem-battery-" + stamp))
    out.mkdir(parents=True, exist_ok=False)
    (out / "responses").mkdir()\n    (out / "resources").mkdir()\n    port = urlparse(base).port or (443 if urlparse(base).scheme == "https" else 80)
    manifest = {
        "started_at":dt.datetime.now().astimezone().isoformat(), "mode":a.mode,
        "engine":a.engine, "model":a.model, "model_path_or_id":a.model_path,
        "base_url":base, "temperature":0, "stream":False, "thinking":True,
        "reasoning_format":"deepseek",
        "cases":[{"task":t,"budget":b,"max_tokens":m} for t,_,b,m in CASES],
        "note":"Client does not change server configuration.",\n        "resource_monitor":{"interval_seconds":a.monitor_interval,"server_pid_argument":a.server_pid,"metrics":"Linux /proc, /proc/diskstats and nvidia-smi; system-wide disk/swap deltas"}}
    }
    for endpoint in ("/health","/props"):
        try: manifest[endpoint[1:]] = get_json(base+endpoint)
        except Exception as e: manifest[endpoint[1:]] = {"capture_error":str(e)}
    (out/"run_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    cases = CASES[:a.limit] if a.limit else CASES
    with (out/"summary.jsonl").open("w",encoding="utf-8") as summary:
        for i,(task,prompt,budget,max_tokens) in enumerate(cases,1):
            payload = {"model":a.model,"messages":[{"role":"user","content":prompt}],
                "temperature":0,"max_tokens":max_tokens,"reasoning_format":"deepseek",
                "reasoning_budget_tokens":budget,
                "chat_template_kwargs":{"enable_thinking":True},"stream":False}
            rec = {"index":i,"task":task,"budget":budget,"max_tokens":max_tokens,
                   "started_at":dt.datetime.now().astimezone().isoformat(),"request":payload}
            try:
                result = post_json(base+"/v1/chat/completions",payload,a.timeout)
                rec["response"] = result
                choice = (result.get("choices") or [{}])[0]
                msg = choice.get("message") or {}
                timing = result.get("timings") or {}
                usage = result.get("usage") or {}
                rec["metrics"] = {
                    "id":result.get("id"),"finish_reason":choice.get("finish_reason"),
                    "prompt_tokens":usage.get("prompt_tokens"),
                    "completion_tokens":usage.get("completion_tokens"),
                    "cached_tokens":(usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
                    "prompt_ms":timing.get("prompt_ms"),"predicted_ms":timing.get("predicted_ms"),
                    "prompt_tokens_per_second":timing.get("prompt_per_second"),
                    "generation_tokens_per_second":timing.get("predicted_per_second"),
                    "content_chars":len(msg.get("content") or ""),
                    "reasoning_chars":len(msg.get("reasoning_content") or "")}
            except urllib.error.HTTPError as e:
                rec["error"]={"http_status":e.code,"body":e.read().decode(errors="replace")}
            except Exception as e:
                rec["error"]={"type":type(e).__name__,"message":str(e)}
            rec["finished_at"] = dt.datetime.now().astimezone().isoformat()
            name = f"{i:02d}-{task}-budget{budget}-max{max_tokens}.json"
            (out/"responses"/name).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+"\n")
            row = dict(rec.get("metrics",rec.get("error",{})))
            row.update({"task":task,"budget":budget,"max_tokens":max_tokens,\n                "resource_metrics":rec.get("resource_metrics"),"resource_monitor_error":rec.get("resource_monitor_error")})
            summary.write(json.dumps(row,ensure_ascii=False)+"\n"); summary.flush()
            print(f"[{i}/{len(cases)}] {task} budget={budget} max={max_tokens}: {row}",flush=True)
            if i < len(cases) and a.pause: time.sleep(a.pause)
    manifest["finished_at"] = dt.datetime.now().astimezone().isoformat()
    (out/"run_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n")
    print("Results:",out.resolve())

if __name__ == "__main__":
    main()
