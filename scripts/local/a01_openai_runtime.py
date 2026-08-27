#!/usr/bin/env python3
"""Run A01 against a local OpenAI-compatible runtime.

The process accepts the A01 prompt as its final positional argument and emits
only the model's textual tool-call response. It is deliberately restricted to
loopback URLs so a real A01 benchmark cannot silently send model prompts to the
Internet.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
SYSTEM_PROMPT = (
    "You are executing LEONES Agentic benchmark A01. Return exactly two JSONL "
    "lines and no markdown or prose. First: {\"tool\":\"lookup_model\","
    "\"arguments\":{\"model_id\":\"MODEL_ID\"}}. Second: "
    "{\"tool\":\"write_report\",\"arguments\":{\"path\":\"report.txt\"}}."
)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--url", default="http://127.0.0.1:8080/v1/chat/completions")
    p.add_argument("--model", required=True)
    p.add_argument("prompt")
    args = p.parse_args()

    parsed = urllib.parse.urlparse(args.url)
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise SystemExit("A01 local runtime requires an http loopback URL")

    system = SYSTEM_PROMPT.replace("MODEL_ID", args.model)
    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": args.prompt},
        ],
        "temperature": 0,
        "max_tokens": 128,
        "stream": False,
    }
    request = urllib.request.Request(
        args.url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"local runtime request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        print("local runtime response has no choices", file=sys.stderr)
        return 3
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        print("local runtime response has no textual content", file=sys.stderr)
        return 3
    print(content.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
