#!/usr/bin/env python3
"""Measure a local inference endpoint without running the agentic battery.

Purpose
-------
This script answers one question: how does the configured inference endpoint
perform for a small, repeatable generation request?

It deliberately does NOT discover hardware, run LOTB, create GitHub commits,
or decide whether a result is verified.

The script currently targets an OpenAI-compatible local HTTP endpoint. Keeping
this boundary small makes it possible to adapt LEONES to llama.cpp, Ollama,
vLLM or another local server without changing the rest of the pipeline.

Example
-------
    python3 scripts/leones-infer.py \
        --url http://127.0.0.1:8080/v1/chat/completions \
        --model local-model

Output is JSON so a later report step can consume it without scraping terminal
text.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser(description="Measure a local OpenAI-compatible inference endpoint")
    parser.add_argument("--url", required=True, help="Chat completions endpoint URL")
    parser.add_argument("--model", required=True, help="Model identifier accepted by the endpoint")
    parser.add_argument("--prompt", default="Explain in one short sentence what a local AI agent is.")
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    payload = {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    request = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw = response.read().decode("utf-8")
    except (urllib.error.URLError, TimeoutError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2))
        return 2
    elapsed = time.perf_counter() - started

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(json.dumps({"status": "error", "error": f"invalid JSON response: {exc}"}, indent=2))
        return 2

    usage = data.get("usage", {}) if isinstance(data, dict) else {}
    completion_tokens = usage.get("completion_tokens")
    prompt_tokens = usage.get("prompt_tokens")
    result = {
        "status": "ok",
        "model": args.model,
        "elapsed_seconds": round(elapsed, 3),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "generation_tokens_per_second": (
            round(completion_tokens / elapsed, 3)
            if isinstance(completion_tokens, (int, float)) and elapsed > 0
            else None
        ),
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
