#!/usr/bin/env python3
"""Historical generic benchmark runner retained for provenance only.

The RC1 path now uses an authorized runtime plan and the canonical A01/runtime
execution flow. This runner must not be extended or used for new measurements.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import uuid
from typing import Any

try:
    from scripts.deprecated.record_benchmark import record_measurement
except ModuleNotFoundError:  # ejecución directa
    from record_benchmark import record_measurement


def run_and_record(
    command: list[str], metadata: dict[str, Any], pattern: str
) -> dict[str, Any]:
    """Run the historical generic adapter command and record observed tok/s."""
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(pattern, output)
    if completed.returncode != 0:
        raise RuntimeError(
            f"benchmark command failed with exit code {completed.returncode}"
        )
    if not match:
        raise ValueError(
            "benchmark output does not contain a tokens-per-second measurement"
        )

    data = dict(metadata)
    data["execution_id"] = str(uuid.uuid4())
    data["tokens_per_second"] = float(match.group(1))
    return record_measurement(data)


def main() -> None:
    """Expose the historical runner as a command-line tool."""
    parser = argparse.ArgumentParser(
        description="Historical runner; use the canonical RC1 runtime path instead"
    )
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--context-tokens", required=True, type=int)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.command:
        parser.error("a runtime command is required")

    metadata = {
        "model": args.model,
        "variant": args.variant,
        "runtime": args.runtime,
        "hardware": args.hardware,
        "workload": args.workload,
        "quantization": args.quantization,
        "context_tokens": args.context_tokens,
    }
    print(run_and_record(args.command, metadata, args.pattern))


if __name__ == "__main__":
    main()
