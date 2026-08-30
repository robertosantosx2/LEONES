#!/usr/bin/env python3
"""Canonical A01 path.

selector -> runtime-selection.v1 gate -> A01 executor -> grader
         -> runtime benchmark -> evidence -> JALON 7 task result.

The CI path uses a controlled trusted runtime; real-runtime evidence is kept
separate and must retain its runtime/model provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKENS_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:tok(?:en)?s?/s|tokens?\s*/\s*s)", re.I
)


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


def execute(
    selection_file: Path,
    runtime_commands: Path,
    workspace: Path,
    output_file: Path,
    prompt: str,
    timeout: float,
) -> tuple[dict[str, Any], str, float]:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(repo_root)
        if not existing_pythonpath
        else f"{repo_root}{os.pathsep}{existing_pythonpath}"
    )
    cmd = [
        sys.executable,
        "scripts/run_a01_selected.py",
        "--selection",
        str(selection_file),
        "--runtime-commands",
        str(runtime_commands),
        "--workspace",
        str(workspace),
        "--prompt",
        prompt,
        "--out",
        str(output_file),
    ]
    output_file.unlink(missing_ok=True)
    started = time.perf_counter()
    proc = subprocess.run(
        cmd, text=True, capture_output=True, timeout=timeout + 10, env=env
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        if output_file.exists():
            raise RuntimeError(
                "A01 executor returned "
                f"{proc.returncode}; refusing to treat a failed run as fresh success.\n"
                f"stdout:\n{proc.stdout[-4000:]}\nstderr:\n{proc.stderr[-4000:]}"
            )
        raise RuntimeError(
            f"A01 executor failed with code {proc.returncode}; no executor result was produced.\n"
            f"stdout:\n{proc.stdout[-4000:]}\nstderr:\n{proc.stderr[-4000:]}"
        )
    if not output_file.exists():
        raise RuntimeError(
            "A01 executor exited successfully but did not produce the requested executor result.\n"
            f"stdout:\n{proc.stdout[-4000:]}\nstderr:\n{proc.stderr[-4000:]}"
        )
    return load_json(output_file), proc.stdout + "\n" + proc.stderr, elapsed


def build_benchmark(
    selection: dict[str, Any],
    result: dict[str, Any],
    raw: str,
    elapsed: float,
    *,
    execution_id: str | None = None,
    finished_at: str | None = None,
) -> dict[str, Any]:
    plans = result.get("runtime_selection", {}).get("execution_plans", [])
    plan = plans[0] if plans else {}
    agentic = result.get("agentic", {})
    outcome = agentic.get("outcome", {})
    runtime = plan.get("runtime", {})
    model = plan.get("model", {})
    tps = extract_tps(raw, result, elapsed)
    wall = agentic.get("metrics", {}).get("runtime_wall_seconds", elapsed)
    execution_id = execution_id or f"a01-{uuid.uuid4().hex}"
    finished_at = finished_at or datetime.now(timezone.utc).isoformat()
    model_id = model.get("id") or plan.get("model_id")
    benchmark = {
        "schema": "runtime-benchmark.v1",
        "schema_version": "runtime-benchmark.v1",
        "status": "measured",
        "measurement_status": "measured",
        "task": "A01",
        "execution_id": execution_id,
        "finished_at": finished_at,
        "runtime": runtime.get("name"),
        "adapter": runtime.get("adapter"),
        "runtime_version": runtime.get("version"),
        "model": model_id,
        "model_id": model_id,
        "model_revision": model.get("revision"),
        "quantization": plan.get("quantization"),
        "hardware": plan.get("hardware", {}),
        "workload": plan.get("workload", {}),
        "wall_seconds": float(wall),
        "tokens_per_second": tps,
        "grader_pass": outcome.get("status") == "success",
        "estimated_tps": plan.get("estimated_tps"),
        "measured_tps": tps,
        "measured": {
            "wall_seconds": float(wall),
            "tokens_per_second": tps,
        },
        "executor_result_sha256": hashlib.sha256(
            json.dumps(result, sort_keys=True).encode()
        ).hexdigest(),
    }
    benchmark["benchmark_evidence_id"] = f"A01:{execution_id}"
    return benchmark


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selection", required=True, type=Path)
    ap.add_argument("--runtime-commands", required=True, type=Path)
    ap.add_argument("--workspace", type=Path, default=Path(".leones/a01-workspace"))
    ap.add_argument("--prompt", default="Execute A01. Return only JSONL tool calls.")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument(
        "--out", type=Path, default=Path("artifacts/a01-runtime-benchmark.v1.json")
    )
    args = ap.parse_args()

    selection = load_json(args.selection)
    if "candidates" not in selection:
        raise SystemExit("input is not selector output: missing candidates")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    executor_out = args.out.with_name("a01-executor-result.json")
    result, raw, elapsed = execute(
        args.selection,
        args.runtime_commands,
        args.workspace,
        executor_out,
        args.prompt,
        args.timeout,
    )
    execution_id = f"a01-{uuid.uuid4().hex}"
    finished_at = datetime.now(timezone.utc).isoformat()
    benchmark = build_benchmark(
        selection,
        result,
        raw,
        elapsed,
        execution_id=execution_id,
        finished_at=finished_at,
    )
    evidence = {
        "schema": "evidence.v1",
        "evidence_id": benchmark["benchmark_evidence_id"],
        "source": "LEONES-A01-runtime-benchmark",
        "selection": selection,
        "runtime_selection": result.get("runtime_selection"),
        "grader": result.get("grader") or result.get("agentic", {}).get("grader"),
        "runtime_benchmark": benchmark,
        "executor_result": result,
    }
    payload = {"evidence": evidence}
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if benchmark["grader_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
