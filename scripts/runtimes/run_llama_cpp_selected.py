#!/usr/bin/env python3
"""Execute an already-authorized LEONES runtime plan with llama.cpp.

This is intentionally the final local execution bridge: it accepts a runtime
plan produced by ``runtime_gate.py``, refuses unauthorized plans, builds a
shell-free llama.cpp command, executes it, and records only observed tok/s.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.runtimes.llama_cpp_adapter import build_command_from_plan, tokens_per_second_pattern
from scripts.run_and_record_benchmark import run_and_record


def run_plan(plan: dict[str, Any], *, model_path: str, prompt: str, hardware: str,
             workload: str, context_tokens: int, executable: str = "llama-cli") -> dict[str, Any]:
    command = build_command_from_plan(
        plan, model_path, prompt, executable=executable, context_tokens=context_tokens
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
    return run_and_record(command, metadata, tokens_per_second_pattern())


def main() -> int:
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
