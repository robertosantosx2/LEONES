#!/usr/bin/env python3
"""A01 execution adapter for a trusted LLMServe/llama.cpp-style runtime."""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from benchmarks.agentic.runner import RunConfig, Trace, build_result
from benchmarks.agentic.adapters.a01_contract import ALLOWED_TOOLS, safe_workspace_path, validate_runtime_plan
from benchmarks.agentic.graders.a01_grader import grade_a01
from benchmarks.evidence.runtime_measurement import build_measurement


def run_runtime(plan: dict[str, Any], prompt: str, *, timeout_seconds: float = 60.0) -> tuple[str, float]:
    """Run the trusted RuntimePlan argv and return stdout plus wall time."""
    validate_runtime_plan(plan)
    command = plan.get("runtime", {}).get("command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError("runtime.command must be a trusted argv list")
    started = time.monotonic()
    completed = subprocess.run([*command, prompt], check=False, capture_output=True, text=True,
                               timeout=timeout_seconds, shell=False)
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(f"runtime exited with code {completed.returncode}")
    return completed.stdout, elapsed


def build_a01_result(plan: dict[str, Any], *, workspace: Path, model_output: str,
                     lookup_model: Callable[[str], dict[str, str]],
                     write_report: Callable[[str, str], str], output_path: str,
                     runtime_seconds: float | None = None) -> dict[str, Any]:
    """Grade one real model response under A01's strict tool contract."""
    trace = Trace()
    config = RunConfig("LEONES-Agentic", "1.0", "A01", "1.0", max_tool_calls=2)
    trace.add("model", name=plan["model"].get("id"), status="completed")
    requests: list[dict[str, Any]] = []
    for line in (line.strip() for line in model_output.splitlines() if line.strip()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("tool") in ALLOWED_TOOLS:
            requests.append(value)
    if len(requests) != 2 or [r.get("tool") for r in requests] != ["lookup_model", "write_report"]:
        raise ValueError("A01 requires exactly lookup_model followed by write_report")
    model_id = requests[0].get("arguments", {}).get("model_id")
    if model_id != "demo-2":
        raise ValueError("A01 requires lookup_model(model_id=demo-2)")
    model = lookup_model(model_id)
    requested_path = requests[1].get("arguments", {}).get("path", output_path)
    safe_path = safe_workspace_path(workspace, requested_path)
    artifact = write_report(str(safe_path), model["name"])
    artifact_path = Path(artifact)
    grader = grade_a01(tool_requests=requests, model=model, artifact_path=artifact_path)
    passed = grader["status"] == "passed"
    trace.add("artifact", name="report.txt", status="verified" if passed else "failed", details={"path": str(artifact_path)})
    trace.add("grader", name=grader["id"], status=grader["status"], details=grader["checks"])
    measurement = build_measurement(
        elapsed_seconds=runtime_seconds or 0.0,
        output=model_output,
        source=str(plan.get("runtime", {}).get("name") or "trusted-runtime"),
    ) if runtime_seconds is not None else None
    metrics: dict[str, Any] = {"tool_calls": 2, "tool_errors": 0, "recovery_count": 0}
    if measurement is not None:
        metrics.update({
            "runtime_wall_seconds": measurement["wall_seconds"],
            "measured_tps": measurement["measured_tps"],
            "measurement_status": measurement["measurement_status"],
        })
    return build_result(config, trace, model=plan["model"], hardware=plan["hardware"],
                        inference=plan.get("inference", {}),
                        outcome={"status": "success" if passed else "failed", "score": grader["score"]},
                        metrics=metrics, runtime=plan["runtime"], scaffold={"name": "runtime-A01"},
                        environment={"mode": "real-runtime"},
                        tools=[{"name": "lookup_model"}, {"name": "write_report"}],
                        grader=grader, evidence_type="measured", evidence_source="LEONES-A01-runtime")


def execute_a01(plan: dict[str, Any], *, prompt: str, workspace: Path,
                lookup_model: Callable[[str], dict[str, str]],
                write_report: Callable[[str, str], str], output_path: str = "report.txt",
                timeout_seconds: float = 60.0) -> dict[str, Any]:
    """End-to-end entry point: runtime-selection.v1 -> trusted runtime -> A01 grader."""
    run_plan = dict(plan)
    run_plan.setdefault("model", {"id": plan.get("model_id", ""), "name": plan.get("model_id", "")})
    run_plan.setdefault("runtime", {})
    run_plan.setdefault("hardware", {})
    output, elapsed = run_runtime(run_plan, prompt, timeout_seconds=timeout_seconds)
    return build_a01_result(run_plan, workspace=workspace, model_output=output,
                            lookup_model=lookup_model, write_report=write_report,
                            output_path=output_path, runtime_seconds=elapsed)
