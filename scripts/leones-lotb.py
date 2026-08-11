#!/usr/bin/env python3
"""Run the LEONES LOTB task battery against a local agent endpoint.

Purpose
-------
This script answers one question: can the configured agent complete the
standard LEONES tasks?

It deliberately does NOT discover hardware, benchmark raw inference, publish
to GitHub, or assign a global verification status.

The initial implementation provides the stable command-line boundary and the
five task identifiers. Task implementations can evolve independently while
the report format remains stable.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request

TASKS = {
    "B01": "memory/locality",
    "B02": "files",
    "B03": "multistep",
    "B04": "recovery",
    "B05": "local coding",
}


def call_agent(url: str, prompt: str, timeout: float) -> dict:
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read()
        return {"status": "completed", "elapsed_seconds": round(time.perf_counter() - started, 3)}
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "error", "error": str(exc), "elapsed_seconds": round(time.perf_counter() - started, 3)}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LEONES LOTB task battery")
    parser.add_argument("--endpoint", required=True, help="Local agent HTTP endpoint")
    parser.add_argument("--task", choices=list(TASKS) + ["all"], default="all")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    selected = TASKS if args.task == "all" else {args.task: TASKS[args.task]}
    results = {}
    for code, description in selected.items():
        prompt = (
            f"LEONES LOTB {code} ({description}). "
            "Complete the task according to the local LOTB specification and report a concise result."
        )
        results[code] = call_agent(args.endpoint, prompt, args.timeout)

    print(json.dumps({"status": "ok", "tasks": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
