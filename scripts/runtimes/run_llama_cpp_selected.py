#!/usr/bin/env python3
"""Execute one already-authorized LEONES runtime plan with llama.cpp.

This is intentionally the final local execution bridge: it accepts a runtime
plan produced by ``runtime_gate.py``, refuses unauthorized plans, builds a
shell-free llama.cpp command, executes it, and records only observed tok/s.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import uuid
from pathlib import Path
from typing import Any

from scripts.record_benchmark import record_measurement
from scripts.runtimes.llama_cpp_adapter import (
    build_command_from_plan,
    tokens_per_second_pattern,
)


def run_plan(
    plan: dict[str, Any],
    *,
    model_path: str,
    prompt: str,
    hardware: str,
    workload: str,
    context_tokens: int,
    executable: str = "llama-cli",
) -> dict[str, Any]:
    """Execute one authorized plan and return its observed measurement."""
    command = build_command_from_plan(
        plan,
        model_path,
        prompt,
        executable=executable,
        context_tokens=context_tokens,
    )
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0:
        raise RuntimeError(
            f"llama.cpp command failed with exit code {completed.returncode}"
        )

    match = re.search(tokens_per_second_pattern(), output)
    if not match:
        raise ValueError(
            "llama.cpp output does not contain a tokens-per-second measurement"
        )

    metadata = {
        "model": plan["model_id"],
        "variant": plan.get("variant") or "default",
        "runtime": plan["runtime"],
        "hardware": hardware,
        "workload": workload,
        "quantization": plan["quantization"],
        "context_tokens": context_tokens,
        "selection_rank": plan.get("selection_rank"),
        "fit_score": plan.get("fit_score"),
        "selection_status": plan.get("selection_status"),
        "execution_id": str(uuid.uuid4()),
        "tokens_per_second": float(match.group(1)),
    }
    return record_measurement(metadata)


def main() -> int:
    """Execute one JSON plan from explicit local inputs and print its result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--context", type=int, required=True)
    parser.add_argument("--executable", default="llama-cli")
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    result = run_plan(
        plan,
        model_path=args.model,
        prompt=args.prompt,
        hardware=args.hardware,
        workload=args.workload,
        context_tokens=args.context,
        executable=args.executable,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
