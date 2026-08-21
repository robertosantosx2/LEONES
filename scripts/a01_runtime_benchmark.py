#!/usr/bin/env python3
"""Canonical A01 path.

selector -> runtime-selection.v1 gate -> A01 executor -> grader
         -> runtime benchmark -> evidence -> Router hand-off.

The existing ``run_a01_selected.py`` remains the concrete executor bridge;
this entry point adds the missing measured-runtime/evidence/Router boundary.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

TOKENS_RE = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?:tok(?:en)?s?/s|tokens?\s*/\s*s)", re.I)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def extract_tps(raw: str, result: dict[str, Any], elapsed: float) -> float | None:
    for key in ("measured_tps", "tokens_per_second", "tok_per_s", "tokens_s"):
        value = result.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    metrics = result.get("agentic", {}).get("metrics", {})
    for key in ("measured_tps", "tokens_per_second"):
        value = metrics.get(key)
        if isinstance(value, (int, float)) and value >= 0:
            return float(value)
    usage = result.get("usage") or result.get("agentic", {}).get("usage")
    if isinstance(usage, dict):
        completion = usage.get("completion_tokens")
        if isinstance(completion, (int, float)) and elapsed > 0:
            return float(completion) / elapsed
    matches = list(TOKENS_RE.finditer(raw))
    return float(matches[-1].group("value")) if matches else None


def execute(selection_file: Path, runtime_commands: Path, workspace: Path, output_file: Path,
            prompt: str, timeout: float) -> tuple[dict[str, Any], str, float]:
    cmd = [
        sys.executable, "scripts/run_a01_selected.py",
        "--selection", str(selection_file),
        "--runtime-commands", str(runtime_commands),
        "--workspace", str(workspace),
        "--prompt", prompt,
        "--out", str(output_file),
    ]
    started = time.perf_counter()
    proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout + 10)
    elapsed = time.perf_counter() - started
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"A01 executor failed: {proc.stdout[-4000:]}\n{proc.stderr[-4000:]}")
    result = load_json(output_file)
    return result, proc.stdout + "\n" + proc.stderr, elapsed


def build_benchmark(selection: dict[str, Any], result: dict[str, Any], raw: str, elapsed: float) -> dict[str, Any]:
    gate = result.get("runtime_selection", {})
    plans = gate.get("execution_plans", [])
    plan = plans[0] if plans else {}
    agentic = result.get("agentic", {})
    outcome = agentic.get("outcome", {})
    runtime = plan.get("runtime", {})
    model = plan.get("model", {})
    tps = extract_tps(raw, result, elapsed)
    wall = agentic.get("metrics", {}).get("runtime_wall_seconds", elapsed)
    return {
        "schema": "runtime-benchmark.v1",
        "status": "measured",
        "task": "A01",
        "runtime": runtime.get("name"),
        "model": model.get("id") or plan.get("model_id"),
        "quantization": plan.get("quantization"),
        "wall_seconds": float(wall),
        "tokens_per_second": tps,
        "grader_pass": outcome.get("status") == "success",
        "selection_status": selection.get("candidates", [{}])[0].get("selection_status"),
        "estimated_tps": plan.get("estimated_tps"),
        "measured_tps": tps,
        "executor_result_sha256": hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest(),
    }


def route(evidence: dict[str, Any]) -> dict[str, Any]:
    benchmark = evidence["runtime_benchmark"]
    passed = bool(benchmark["grader_pass"])
    return {
        "schema": "router-decision.v1",
        "decision": "accept" if passed else "reject",
        "candidate": {
            "model": benchmark.get("model"),
            "runtime": benchmark.get("runtime"),
            "quantization": benchmark.get("quantization"),
        },
        "reason": "A01 passed; runtime is now backed by measured evidence" if passed else "A01 failed",
        "evidence_ref": evidence["evidence_id"],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True, type=Path, help="selector output")
    ap.add_argument("--runtime-commands", required=True, type=Path, help="trusted runtime argv map")
    ap.add_argument("--workspace", type=Path, default=Path(".leones/a01-workspace"))
    ap.add_argument("--prompt", default="Execute A01. Return only JSONL tool calls.")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--out", type=Path, default=Path("artifacts/a01-runtime-benchmark.v1.json"))
    args = ap.parse_args()

    selection = load_json(args.selection)
    if "candidates" not in selection:
        raise SystemExit("input is not selector output: missing candidates")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    executor_out = args.out.with_name("a01-executor-result.json")
    result, raw, elapsed = execute(args.selection, args.runtime_commands, args.workspace, executor_out, args.prompt, args.timeout)
    benchmark = build_benchmark(selection, result, raw, elapsed)
    evidence = {
        "schema": "evidence.v1",
        "evidence_id": f"A01:{benchmark.get('model')}:{benchmark.get('runtime')}",
        "source": "LEONES-A01-runtime-benchmark",
        "selection": selection,
        "runtime_selection": result.get("runtime_selection"),
        "grader": result.get("grader") or result.get("agentic", {}).get("grader"),
        "runtime_benchmark": benchmark,
        "executor_result": result,
    }
    decision = route(evidence)
    payload = {"evidence": evidence, "router": decision}
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if decision["decision"] == "accept" else 2


if __name__ == "__main__":
    raise SystemExit(main())
