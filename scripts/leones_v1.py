#!/usr/bin/env python3
"""Small user-facing entry point for the first LEONES V1 workflow.

This file is deliberately boring. It does not contain a new recommendation
engine. Its job is to give a person a simple command that explains what LEONES
can see on the current machine before any physical run is requested.

A reader with little programming experience can think of this script as a
front door: it collects basic machine facts and points at the contracts that
already contain the real logic. It must never invent a performance result.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# These are references to existing contracts, not a second source of truth.
CONTRACTS = {
    "preflight": ROOT / "schemas/leones-v1-preflight.v1.json",
    "decision": ROOT / "schemas/leones-ods-magnitude-decision.v1.json",
    "recommendation": ROOT / "schemas/leones-recommendation.v1.json",
    "recommendation_output": ROOT / "schemas/leones-recommendation-output.v1.json",
    "e2e_operation": ROOT / "schemas/leones-e2e-operation.v1.json",
    "e2e_trace": ROOT / "schemas/leones-e2e-trace.v1.json",
}


def build_preflight() -> dict[str, object]:
    """Return only facts that can be observed without running a benchmark."""
    runtimes = {}
    for command in ("llama-cli", "ollama", "python"):
        runtimes[command] = shutil.which(command)

    return {
        "schema": "leones-v1-preflight.v1",
        "status": "observed",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": os.cpu_count(),
        "runtimes_detected": runtimes,
        "contracts_present": {
            name: path.is_file() for name, path in CONTRACTS.items()
        },
        "note": (
            "Preflight observes the host only. It does not measure tokens per "
            "second and does not create a recommendation."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LEONES V1 front door: inspect the host without benchmarking it."
    )
    parser.add_argument(
        "command",
        choices=("preflight",),
        help="operation to perform; physical execution is deliberately separate",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="format the JSON result for a human reader",
    )
    args = parser.parse_args()

    if args.command == "preflight":
        result = build_preflight()
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=True))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
