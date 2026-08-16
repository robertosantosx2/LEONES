#!/usr/bin/env python3
"""Minimal local smoke test for an LLM runtime.

This first version intentionally uses only the Python standard library.
It validates the local test-package contract without coupling LEONES to a
specific inference runtime.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from datetime import datetime, timezone


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line interface."""
    parser = argparse.ArgumentParser(
        description="LEONES local LLM smoke-test harness."
    )
    parser.add_argument(
        "--prompt",
        default="Hello from a local LLM test.",
        help="Prompt recorded in the test result.",
    )
    parser.add_argument(
        "--model",
        default="unknown",
        help="Model identifier recorded in the test result.",
    )
    parser.add_argument(
        "--runtime",
        default="unknown",
        help="Inference runtime identifier recorded in the result.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path.",
    )
    return parser


def build_result(args: argparse.Namespace) -> dict[str, object]:
    """Create a reproducible environment/result envelope."""
    started = time.perf_counter()
    finished = time.perf_counter()

    return {
        "schema_version": "0.1",
        "status": "harness_ready",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model": args.model,
        "runtime": args.runtime,
        "prompt": args.prompt,
        "response": None,
        "metrics": {
            "wall_time_seconds": round(finished - started, 6),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "notes": [
            "This is an experimental harness, not an official benchmark.",
            "No model was downloaded or executed by this version.",
        ],
    }


def main() -> int:
    """Run the local smoke-test harness."""
    args = build_parser().parse_args()
    result = build_result(args)
    payload = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    sys.exit(main())
