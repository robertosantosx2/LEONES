#!/usr/bin/env python3
"""Record native Ollama /api/generate physical benchmark evidence v1.1."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path

from scripts.runtime_benchmark_evidence import hardware, sha256_text, summarize, version


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def post_json(url: str, payload: dict, timeout: float) -> list[dict]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    first_output_ms = None
    rows: list[dict] = []
    with urllib.request.urlopen(request, timeout=timeout) as response:
        for raw in response:
            if not raw.strip():
                continue
            if first_output_ms is None:
                first_output_ms = (time.perf_counter() - started) * 1000
            rows.append(json.loads(raw))
    if not rows:
        raise RuntimeError("Ollama returned no response chunks")
    final = rows[-1]
    final["_client_total_ms"] = (time.perf_counter() - started) * 1000
    final["_client_ttft_ms"] = first_output_ms
    return rows


def show_model(base_url: str, model: str, timeout: float) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/show",
        data=json.dumps({"name": model}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def run_one(base_url: str, model: str, prompt: str, *, context: int, temperature: float,
            top_p: float | None, seed: int | None, timeout: float) -> dict:
    options = {"num_ctx": context, "temperature": temperature}
    if top_p is not None:
        options["top_p"] = top_p
    if seed is not None:
        options["seed"] = seed
    rows = post_json(
        f"{base_url.rstrip('/')}/api/generate",
        {"model": model, "prompt": prompt, "stream": True, "options": options},
        timeout,
    )
    final = rows[-1]
    eval_count = final.get("eval_count")
    eval_duration = final.get("eval_duration")
    prompt_eval_duration = final.get("prompt_eval_duration")
    total_duration = final.get("total_duration")
    tps = (eval_count / eval_duration * 1_000_000_000) if eval_count and eval_duration else None
    return {
        "ttft_ms": final.get("_client_ttft_ms"),
        "first_output_ms": final.get("_client_ttft_ms"),
        "generation_time_ms": (eval_duration / 1_000_000) if eval_duration else None,
        "output_tokens": eval_count,
        "tokens_per_second": tps,
        "total_time_ms": (total_duration / 1_000_000) if total_duration else final["_client_total_ms"],
        "peak_memory_mb": None,
        "peak_vram_mb": None,
        "power_w": None,
        "exit_code": 0 if final.get("done") else 1,
        "stdout": json.dumps({"response": "".join(r.get("response", "") for r in rows), "eval_count": eval_count,
                              "eval_duration": eval_duration, "prompt_eval_count": final.get("prompt_eval_count"),
                              "prompt_eval_duration": prompt_eval_duration, "total_duration": total_duration}, ensure_ascii=False),
        "stderr": "",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", required=True)
    p.add_argument("--prompt", required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--artifact-output", type=Path, required=True)
    p.add_argument("--base-url", default="http://127.0.0.1:11434")
    p.add_argument("--model-id", required=True)
    p.add_argument("--model-name", required=True)
    p.add_argument("--revision", default="local")
    p.add_argument("--quantization", default="unknown")
    p.add_argument("--context", type=int, default=2048)
    p.add_argument("--input-tokens", type=int, default=None)
    p.add_argument("--output-token-limit", type=int, default=128)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--top-p", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--iterations", type=int, default=3)
    p.add_argument("--timeout", type=float, default=120.0)
    args = p.parse_args()

    show = show_model(args.base_url, args.model, args.timeout)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    artifact_text = json.dumps(show, indent=2, ensure_ascii=False) + "\n"
    args.artifact_output.write_text(artifact_text, encoding="utf-8")
    artifact_sha = hashlib.sha256(artifact_text.encode()).hexdigest()

    for _ in range(args.warmup):
        run_one(args.base_url, args.model, args.prompt, context=args.context, temperature=args.temperature,
                top_p=args.top_p, seed=args.seed, timeout=args.timeout)

    started = now()
    measurements = []
    for iteration in range(1, args.iterations + 1):
        item = run_one(args.base_url, args.model, args.prompt, context=args.context, temperature=args.temperature,
                       top_p=args.top_p, seed=args.seed, timeout=args.timeout)
        item["iteration"] = iteration
        measurements.append(item)

    ollama = shutil.which("ollama") or "ollama"
    binary = Path(ollama).resolve() if shutil.which("ollama") else Path(ollama)
    evidence = {
        "schema": "runtime-benchmark-evidence.v1.1",
        "execution_id": "rt-" + uuid.uuid4().hex,
        "timestamp_start": started,
        "timestamp_end": now(),
        "model": {"id": args.model_id, "name": args.model_name, "revision": args.revision, "source": "ollama-local",
                   "artifact": f"ollama://{args.model}", "quantization": args.quantization, "context_length": args.context},
        "protocol": {"prompt_protocol_id": "concise-paragraph-v1", "prompt_sha256": sha256_text(args.prompt),
                     "input_tokens": args.input_tokens, "output_token_limit": args.output_token_limit,
                     "temperature": args.temperature, "top_p": args.top_p, "seed": args.seed, "context": args.context,
                     "warmup_iterations": args.warmup, "measurement_iterations": args.iterations},
        "runtime": {"name": "ollama", "version": version(ollama), "revision": None, "backend": "cpu",
                    "binary": str(binary), "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest() if binary.is_file() else None,
                    "command": ["ollama", "api", "/api/generate", "--model", args.model]},
        "hardware": hardware(), "measurements": measurements, "summary": summarize(measurements),
        "process": {"exit_code": max(x["exit_code"] for x in measurements), "stdout": "\n".join(x["stdout"] for x in measurements), "stderr": ""},
        "artifact": {"path": str(args.artifact_output), "sha256": artifact_sha, "size": args.artifact_output.stat().st_size},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"execution_id": evidence["execution_id"], "output": str(args.output), "summary": evidence["summary"]}, indent=2))
    return 0 if evidence["process"]["exit_code"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
