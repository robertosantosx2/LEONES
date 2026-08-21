#!/usr/bin/env python3
"""A01 execution adapter boundary for LLMServe/llama.cpp.

The adapter deliberately separates process execution from task tools. The
runtime command is supplied by a trusted RuntimePlan; model output is parsed
by the caller and can only select the allow-listed A01 operations.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable

from runner import RunConfig, Trace, build_result, execute_tool, write_result
from a01_contract import A01Context, ALLOWED_TOOLS, safe_workspace_path, validate_runtime_plan


def run_runtime(plan: dict[str, Any], prompt: str, *, timeout_seconds: float = 60.0) -> tuple[str, float]:
    """Run a trusted runtime command and return stdout plus elapsed time.

    `runtime.command` must be constructed by LEONES runtime integration, not
    from model-generated text. Shell invocation is intentionally disabled.
    """
    validate_runtime_plan(plan)
    command = plan.get("runtime", {}).get("command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError("runtime.command must be a trusted argv list")
    started = time.monotonic()
    completed = subprocess.run(
        [*command, prompt],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        shell=False,
    )
    elapsed = time.monotonic() - started
    if completed.returncode != 0:
        raise RuntimeError(f"runtime exited with code {completed.returncode}")
    return completed.stdout, elapsed


def build_a01_result(
    plan: dict[str, Any],
    *,
    workspace: Path,
    model_output: str,
    lookup_model: Callable[[str], dict[str, str]],
    write_report: Callable[[str, str], str],
    output_path: str,
) -> dict[str, Any]:
    """Convert one trusted model invocation into a measured A01 result.

    The current reference parser accepts only explicit JSON tool requests of
    the form {"tool":"lookup_model","arguments":{"model_id":"demo-2"}}
    followed by write_report. Free-form text is never interpreted as a tool.
    """
    trace = Trace()
    config = RunConfig("LEONES-Agentic", "1.0", "A01", "1.0", max_tool_calls=2)
    trace.add("model", name=plan["model"].get("id"), status="completed")

    lines = [line.strip() for line in model_output.splitlines() if line.strip()]
    requests: list[dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and value.get("tool") in ALLOWED_TOOLS:
            requests.append(value)

    if len(requests) != 2:
        raise ValueError("A01 requires exactly two explicit allow-listed tool requests")
    if requests[0].get("tool") != "lookup_model" or requests[1].get("tool") != "write_report":
        raise ValueError("A01 tool sequence is invalid")

    model = execute_tool(
        trace, "lookup_model", lookup_model,
        model_id=requests[0].get("arguments", {}).get("model_id"),
        tool_calls_so_far=0, max_tool_calls=2,
    )
    requested_path = requests[1].get("arguments", {}).get("path", output_path)
    safe_path = safe_workspace_path(workspace, requested_path)
    artifact = execute_tool(
        trace, "write_report", write_report,
        path=str(safe_path), name=model["name"],
        tool_calls_so_far=1, max_tool_calls=2,
    )
    content = Path(artifact).read_text(encoding="utf-8")
    passed = model["name"] == "Beta" and "Beta" in content
    trace.add("artifact", name="report.txt", status="verified" if passed else "failed")
    trace.add("grader", name="A01-grader", status="passed" if passed else "failed")

    return build_result(
        config, trace,
        model=plan["model"], hardware=plan["hardware"], inference=plan.get("inference", {}),
        outcome={"status": "success" if passed else "failed", "score": 1.0 if passed else 0.0},
        metrics={"tool_calls": 2, "tool_errors": 0, "recovery_count": 0},
        runtime=plan["runtime"], scaffold={"name": "LLMServe-A01"},
        environment={"mode": "real-runtime"},
        tools=[{"name": "lookup_model"}, {"name": "write_report"}],
        grader={"id": "A01-grader", "version": "1.0", "status": "passed" if passed else "failed"},
        evidence_type="measured", evidence_source="LEONES-A01-LLMServe",
    )
