#!/usr/bin/env python3
"""Execute an inference adapter and record its measured throughput.

The runner executes one explicit command and extracts an observed tok/s value.
It does not select models, authorize runtime plans or publish results.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import uuid
from typing import Any

from scripts.record_benchmark import record_measurement


def run_and_record(
    command: list[str], metadata: dict[str, Any], pattern: str
) -> dict[str, Any]:
    """Run an adapter command and record only an observed tok/s value."""
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
    """Expose the runner as a command-line tool."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pattern", required=True, help="Regex cuyo primer grupo contiene tok/s"
    )
    parser.add_argument("--model", required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--quantization", required=True)
    parser.add_argument("--context-tokens", required=True, type=int)
    parser.add_argument(
        "command", nargs=argparse.REMAINDER, help="Comando del adaptador de runtime"
    )
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
    result = run_and_record(args.command, metadata, args.pattern)
    print(result)


if __name__ == "__main__":
    main()
