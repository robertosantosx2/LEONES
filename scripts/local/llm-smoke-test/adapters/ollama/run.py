#!/usr/bin/env python3
"""Run a local Ollama generation and emit normalized JSON."""

from __future__ import annotations

import argparse
import json
import platform
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = "0.1"
DEFAULT_HOST = "http://127.0.0.1:11434"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LEONES Ollama local smoke test")
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", default="Say hello in one short sentence.")
    parser.add_argument("--new-tokens", type=int, default=32)
    parser.add_argument("--context", type=int, default=2048)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--output", type=Path, default=None)
    return parser.parse_args()


def ns_to_ms(value: object) -> float | None:
    return (
        round(float(value) / 1_000_000, 3) if isinstance(value, (int, float)) else None
    )


def tokens_per_second(tokens: object, duration_ns: object) -> float | None:
    if (
        not isinstance(tokens, (int, float))
        or not isinstance(duration_ns, (int, float))
        or duration_ns <= 0
    ):
        return None
    return round(float(tokens) / (float(duration_ns) / 1_000_000_000), 3)


def main() -> int:
    args = parse_args()
    started = time.perf_counter()
    endpoint = args.host.rstrip("/") + "/api/generate"
    result = {
        "schema_version": SCHEMA_VERSION,
        "test": {"name": "llm-smoke-test", "mode": "experimental"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "model": {
            "id": args.model,
            "revision": None,
            "parameter_count": None,
            "quantization": None,
            "context_length": args.context,
        },
        "runtime": {"name": "Ollama", "version": None, "adapter": "ollama"},
        "hardware": {
            "os": platform.platform(),
            "architecture": platform.machine(),
            "cpu": platform.processor() or None,
            "ram_bytes": None,
            "gpu": None,
            "vram_bytes": None,
        },
        "configuration": {
            "prompt_tokens": None,
            "requested_new_tokens": args.new_tokens,
            "temperature": None,
            "seed": args.seed,
            "batch_size": None,
            "context_tokens": args.context,
        },
        "warmup": {"enabled": False, "runs": 0},
        "repetitions": 1,
        "metrics": {
            "ttft_ms": None,
            "generation_ms": None,
            "total_ms": None,
            "prompt_tokens": None,
            "generated_tokens": None,
            "tokens_per_second": None,
            "peak_ram_bytes": None,
            "peak_vram_bytes": None,
        },
        "result": {"status": "error", "error": None},
    }

    payload = {
        "model": args.model,
        "prompt": args.prompt,
        "stream": False,
        "options": {"num_predict": args.new_tokens, "num_ctx": args.context},
    }
    if args.seed is not None:
        payload["options"]["seed"] = args.seed

    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            data = json.loads(response.read().decode("utf-8"))
        elapsed_ms = (time.perf_counter() - started) * 1000
        result["metrics"]["total_ms"] = round(elapsed_ms, 3)
        result["metrics"]["prompt_tokens"] = data.get("prompt_eval_count")
        result["metrics"]["generated_tokens"] = data.get("eval_count")
        result["metrics"]["generation_ms"] = ns_to_ms(data.get("eval_duration"))
        result["metrics"]["tokens_per_second"] = tokens_per_second(
            data.get("eval_count"), data.get("eval_duration")
        )
        result["metrics"]["ttft_ms"] = ns_to_ms(data.get("prompt_eval_duration"))
        result["configuration"]["prompt_tokens"] = data.get("prompt_eval_count")
        result["result"]["status"] = "ok"
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        result["result"]["error"] = str(exc)

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0 if result["result"]["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
