#!/usr/bin/env python3
"""Canonical A01 runtime path.

selector -> runtime-selection.v1 -> A01 executor -> grader -> runtime benchmark
         -> evidence -> Router hand-off

This deliberately wraps the already existing A01 executor instead of creating a
second executor.  The executor remains the source of truth for task execution
and grading; this layer adds the missing measured-runtime/evidence hand-off.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


TOKENS_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:tok(?:en)?s?/s|tokens?\s*/\s*s)", re.I)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def extract_tokens_per_second(stdout: str, result: dict[str, Any]) -> float | None:
    for key in ("tokens_per_second", "tok_per_s", "tokens_s"):
        value = result.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    usage = result.get("usage")
    if isinstance(usage, dict):
        completion = usage.get("completion_tokens")
        elapsed = result.get("runtime_wall_seconds") or result.get("elapsed_seconds")
        if isinstance(completion, (int, float)) and isinstance(elapsed, (int, float)) and elapsed > 0:
            return float(completion) / float(elapsed)
    matches = list(TOKENS_RE.finditer(stdout))
    if matches:
        return float(matches[-1].group("value"))
    return None


def run_executor(selection_file: Path, task: str, executor: str) -> tuple[dict[str, Any], str, float]:
    cmd = [sys.executable, executor, "--selection", str(selection_file), "--task", task]
    started = time.perf_counter()
    proc = subprocess.run(cmd, text=True, capture_output=True)
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        raise RuntimeError(
            "A01 executor failed (exit %s):\n%s\n%s"
            % (proc.returncode, proc.stdout[-4000:], proc.stderr[-4000:])
        )
    # Existing executor output is expected to contain a JSON object on the last
    # non-empty line. Keep stdout intact as raw evidence for auditability.
    result: dict[str, Any] | None = None
    for line in reversed([x.strip() for x in proc.stdout.splitlines() if x.strip()]):
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            result = parsed
            break
    if result is None:
        raise RuntimeError("A01 executor produced no JSON result")
    return result, proc.stdout, elapsed


def build_benchmark(selection: dict[str, Any], result: dict[str, Any], wall_seconds: float, raw_stdout: str) -> dict[str, Any]:
    measured = result.get("runtime_wall_seconds")
    if not isinstance(measured, (int, float)) or measured <= 0:
        measured = wall_seconds
    tokens_s = extract_tokens_per_second(raw_stdout, result)
    runtime = selection.get("runtime") or selection.get("runtime_id")
    model = selection.get("model") or selection.get("model_id")
    return {
        "schema": "runtime-benchmark.v1",
        "status": "measured",
        "runtime": runtime,
        "model": model,
        "quantization": selection.get("quantization"),
        "task": "A01",
        "wall_seconds": float(measured),
        "tokens_per_second": tokens_s,
        "grader_pass": bool(result.get("passed", result.get("ok", False))),
        "executor_result_ref": "inline",
        "raw_executor_sha256": __import__("hashlib").sha256(raw_stdout.encode("utf-8")).hexdigest(),
    }


def route(evidence: dict[str, Any]) -> dict[str, Any]:
    benchmark = evidence["runtime_benchmark"]
    passed = bool(benchmark.get("grader_pass"))
    return {
        "schema": "router-decision.v1",
        "decision": "accept" if passed else "reject",
        "candidate": {
            "model": benchmark.get("model"),
            "runtime": benchmark.get("runtime"),
            "quantization": benchmark.get("quantization"),
        },
        "reason": "A01 grader passed with measured runtime evidence" if passed else "A01 grader failed",
        "evidence_ref": evidence["evidence_id"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True, type=Path, help="runtime-selection.v1 JSON produced by the selector")
    ap.add_argument("--task", default="A01")
    ap.add_argument("--executor", default="benchmarks/agentic/adapters/llmserve_a01.py")
    ap.add_argument("--out", type=Path, default=Path("artifacts/a01-runtime-benchmark.v1.json"))
    args = ap.parse_args()

    if args.task != "A01":
        raise SystemExit("this entry point is intentionally scoped to A01")
    selection = load_json(args.selection)
    if selection.get("schema") not in ("runtime-selection.v1", None):
        raise SystemExit("selection is not runtime-selection.v1")

    result, raw_stdout, wall = run_executor(args.selection, args.task, args.executor)
    benchmark = build_benchmark(selection, result, wall, raw_stdout)
    evidence = {
        "schema": "evidence.v1",
        "evidence_id": f"A01:{benchmark.get('model')}:{benchmark.get('runtime')}",
        "source": "A01/runtime-benchmark",
        "selection_schema": "runtime-selection.v1",
        "grader": result.get("grader") or result.get("grade"),
        "runtime_benchmark": benchmark,
        "executor_result": result,
    }
    decision = route(evidence)
    payload = {"evidence": evidence, "router": decision}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if decision["decision"] == "accept" else 2


if __name__ == "__main__":
    raise SystemExit(main())
