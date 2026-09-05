#!/usr/bin/env python3
"""Run the canonical LEONES Leo001-Leo010 suite against a selected model."""
from __future__ import annotations

import argparse
import ast
import json
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from runtime_selection.hermes import select_model

ROOT = Path(__file__).resolve().parents[1]
TASK_FILE = ROOT / "benchmarks/agentic/tasks.yaml"


def load_tasks(path: Path = TASK_FILE) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- id:"):
            if current:
                tasks.append(current)
            current = {"id": line.split(":", 1)[1].strip()}
            continue
        if current is None or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                current[key.strip()] = ast.literal_eval(value)
            except (SyntaxError, ValueError):
                current[key.strip()] = value
        else:
            current[key.strip()] = value.strip('"')
    if current:
        tasks.append(current)
    return tasks


def _post(base_url: str, payload: dict[str, Any], timeout: int) -> tuple[dict[str, Any], float]:
    url = base_url.rstrip("/") + "/chat/completions"
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": "Bearer not-needed"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body, time.perf_counter() - started


def run_task(task: dict[str, Any], *, base_url: str, model: str, runs: int, timeout: int) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    prompt = (
        f"LEONES benchmark {task['id']} ({task.get('family', 'unknown')}): "
        f"{task.get('objective', task.get('title', 'Complete the task.'))}\n"
        f"Constraints: {', '.join(task.get('constraints', []))}\n"
        "Return a concise completion; do not claim tool execution that you did not perform."
    )
    for index in range(runs):
        try:
            body, elapsed = _post(base_url, {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 256}, timeout)
            usage = body.get("usage") or {}
            completion_tokens = usage.get("completion_tokens")
            samples.append({"run": index + 1, "status": "ok", "latency_seconds": round(elapsed, 4), "completion_tokens": completion_tokens, "output_tokens_per_second": round(completion_tokens / elapsed, 3) if completion_tokens and elapsed > 0 else None})
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            samples.append({"run": index + 1, "status": "error", "error_type": type(exc).__name__})

    good = [s for s in samples if s["status"] == "ok"]
    measured_tps = [s["output_tokens_per_second"] for s in good if s["output_tokens_per_second"] is not None]
    return {
        "benchmark_id": task["id"],
        "family": task.get("family"),
        "title": task.get("title"),
        "grader": task.get("grader"),
        "runs": samples,
        "successful_runs": len(good),
        "mean_latency_seconds": round(statistics.mean(s["latency_seconds"] for s in good), 4) if good else None,
        "mean_output_tokens_per_second": round(statistics.mean(measured_tps), 3) if measured_tps else None,
        "evidence_type": "measured" if good else "reported",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="LEONES Leo001-Leo010 benchmark suite")
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible /v1 base URL")
    parser.add_argument("--model")
    parser.add_argument("--decision-json", type=Path)
    parser.add_argument("--select-with-hermes", action="store_true")
    parser.add_argument("--task", default="general")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "task-benchmark-latest.json")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be >= 1")

    model = args.model
    selection = None
    if args.select_with_hermes:
        if not args.decision_json:
            parser.error("--select-with-hermes requires --decision-json")
        decision = json.loads(args.decision_json.read_text(encoding="utf-8"))
        selection = select_model(decision.get("candidates", []), task=args.task)
        model = selection["selected_model_id"]
    if not model:
        parser.error("provide --model or --select-with-hermes")

    results = [run_task(task, base_url=args.base_url, model=model, runs=args.runs, timeout=args.timeout) for task in load_tasks()]
    document = {
        "schema_version": "leones-task-benchmark.v1",
        "benchmark_family": "Leo",
        "selector": selection or {"selector": "user_or_stack", "selected_model_id": model},
        "model": model,
        "endpoint": args.base_url,
        "task_count": len(results),
        "tasks": results,
        "repeatable": True,
        "repeat_instruction": "Repeat with --select-with-hermes for a fresh Hermes-selected model, or --model for a known candidate.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"LEONES Leo benchmark — model: {model}")
    print("benchmark             family              latency(s)   tok/s       status")
    print("-" * 82)
    for result in results:
        print(f"{result['benchmark_id']:<21} {str(result['family']):<19} {str(result['mean_latency_seconds']):<12} {str(result['mean_output_tokens_per_second']):<11} {result['evidence_type']}")
    print(f"\nSaved: {args.output}")
    print("Repeat with --select-with-hermes for another Hermes-selected model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
