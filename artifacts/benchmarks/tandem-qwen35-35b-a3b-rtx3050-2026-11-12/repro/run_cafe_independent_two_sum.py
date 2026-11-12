#!/usr/bin/env python3
"""Run one monitored, independent two_sum request against an already-running cafe-llama.cpp server.

This script never starts, stops, or reconfigures the server. It writes a complete
manifest and response record to a new output directory. Python standard library only,
plus the experiment's existing resource_monitor.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import pathlib
import sys
import urllib.error
import urllib.request


DEFAULT_MODEL = pathlib.Path.home() / "models/tandem-qwen35/Qwen_Qwen3.5-35B-A3B-IQ2_XXS.gguf"
DEFAULT_OUTPUT = pathlib.Path.home() / "cafe-llama.cpp-qwen35-independent"


def load_request_sampler(script_path: pathlib.Path):
    spec = importlib.util.spec_from_file_location("leones_resource_monitor", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load resource monitor: {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.RequestSampler


def get_json(url: str, timeout: int = 20):
    with urllib.request.urlopen(url, timeout=timeout) as response:
        return json.loads(response.read())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18086")
    parser.add_argument("--port", type=int, default=18086)
    parser.add_argument("--pid", type=int, required=True, help="PID of the already-running server")
    parser.add_argument("--model", type=pathlib.Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--monitor-script", type=pathlib.Path)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--reasoning-budget-tokens", type=int, default=128)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).resolve().parent
    repo_root = script_dir.parents[4]
    monitor_script = args.monitor_script or (
        repo_root / "artifacts/benchmarks/tandem-qwen35-35b-a3b-rtx3050-2026-11-12/repro/resource_monitor.py"
    )
    if not monitor_script.is_file():
        raise SystemExit(f"Resource monitor not found: {monitor_script}")
    if not args.model.is_file():
        raise SystemExit(f"Model file not found: {args.model}")

    out = args.output.expanduser().resolve()
    if out.exists():
        if not out.is_dir() or any(out.iterdir()):
            raise SystemExit(f"Output path already exists and is not empty: {out}")
    else:
        out.mkdir(parents=True)
    (out / "resources").mkdir(exist_ok=True)
    (out / "responses").mkdir(exist_ok=True)

    proc = pathlib.Path(f"/proc/{args.pid}")
    if not proc.exists():
        raise SystemExit(f"Server PID does not exist: {args.pid}")
    exe = (proc / "exe").resolve()
    cwd = (proc / "cwd").resolve()
    cmdline = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
    if exe.name != "llama-server" or "llama-server" not in cmdline:
        raise SystemExit(f"PID does not identify llama-server: exe={exe}; cmdline={cmdline}")

    base = args.base_url.rstrip("/")
    health = get_json(base + "/health")
    props = get_json(base + "/props")
    prompt = (
        "Escribe una función Python two_sum(nums, target) que devuelva los índices "
        "de dos elementos distintos cuya suma sea target. Requisitos: complejidad O(n), "
        "admitir números negativos y duplicados, no reutilizar el mismo índice y "
        "devolver None si no existe solución. Explica brevemente el algoritmo y "
        "proporciona tres pruebas, incluyendo un duplicado y un número negativo. "
        "Presenta código completo."
    )
    payload = {
        "model": str(args.model),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": args.max_tokens,
        "reasoning_format": "deepseek",
        "reasoning_budget_tokens": args.reasoning_budget_tokens,
        "chat_template_kwargs": {"enable_thinking": True},
        "stream": False,
    }
    created = dt.datetime.now().astimezone().isoformat()
    manifest = {
        "experiment": "independent-two-sum",
        "methodology": "Nepenthes",
        "engine": "cafe-llama.cpp",
        "build": props.get("build_info"),
        "model": str(args.model),
        "server_pid": args.pid,
        "server_executable": str(exe),
        "server_working_directory": str(cwd),
        "server_cmdline": cmdline,
        "base_url": base,
        "created_at": created,
        "health": health,
        "props": props,
        "request": payload,
        "monitor_script": str(monitor_script.resolve()),
        "notes": [
            "Exploratory single-run task; not a controlled cross-engine benchmark.",
            "An accepted reasoning_budget_tokens field does not prove the server applied that budget.",
            "Cached prompt tokens must be reported separately; cached prefill is not a cold-prefill measurement.",
        ],
    }
    manifest_path = out / "manifest.json"
    if manifest_path.exists():
        raise SystemExit(f"Refusing to overwrite {manifest_path}")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    RequestSampler = load_request_sampler(monitor_script)
    sampler = RequestSampler(out / "resources", "independent-two-sum",
                             args.port, args.pid, 1.0, str(args.model))
    record = {
        "task": "two_sum",
        "started_at": dt.datetime.now().astimezone().isoformat(),
        "request": payload,
    }
    sampler.start()
    try:
        request = urllib.request.Request(
            base + "/v1/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            result = json.loads(response.read())
        record["response"] = result
        choice = (result.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = result.get("usage") or {}
        timing = result.get("timings") or {}
        record["metrics"] = {
            "finish_reason": choice.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens"),
            "completion_tokens": usage.get("completion_tokens"),
            "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens"),
            "prompt_tokens_per_second": timing.get("prompt_per_second"),
            "generation_tokens_per_second": timing.get("predicted_per_second"),
            "reasoning_chars": len(message.get("reasoning_content") or ""),
            "content_chars": len(message.get("content") or ""),
        }
    except urllib.error.HTTPError as error:
        record["error"] = {
            "http_status": error.code,
            "body": error.read().decode(errors="replace"),
        }
    except Exception as error:
        record["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        record["resource_metrics"] = sampler.finish()

    record["finished_at"] = dt.datetime.now().astimezone().isoformat()
    response_path = out / "responses/independent-two-sum.json"
    if response_path.exists():
        raise SystemExit(f"Refusing to overwrite {response_path}")
    response_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({
        "output": str(out),
        "error": record.get("error"),
        "metrics": record.get("metrics"),
        "resource_metrics": record.get("resource_metrics"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
