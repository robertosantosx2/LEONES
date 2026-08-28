#!/usr/bin/env python3
"""Execute one already-authorized llama.cpp plan and record observations.

This is the final local execution bridge for the llama.cpp fallback path. It
accepts a plan produced by LEONES' runtime gate, refuses unauthorized plans,
builds a shell-free command through the canonical adapter, and delegates the
actual subprocess/result capture to the existing benchmark recorder.

The script does **not** choose a model, authorize a plan, install/download a
runtime, benchmark hardware or publish the result. Those responsibilities stay
outside the runner so selection, execution, measurement and publication remain
separate contracts.

For reproducible RC1 measurements, pass an explicit context. The adapter then
also applies ``--simple-io``, ``--single-turn`` and a bounded output length.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.run_and_record_benchmark import run_and_record
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
    """Execute one authorized plan and return the recorder's observed result."""
    command = build_command_from_plan(
        plan,
        model_path,
        prompt,
        executable=executable,
        context_tokens=context_tokens,
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
    }

    # run_and_record owns subprocess execution and metric extraction. Keeping
    # that logic there prevents the runtime runner from becoming a second
    # benchmark implementation.
    return run_and_record(command, metadata, tokens_per_second_pattern())


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
