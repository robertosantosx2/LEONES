#!/usr/bin/env python3
"""Safety-first contract adapter for a real A01 runtime integration.

This module intentionally does not start a model. It validates the boundary
between a normalized RuntimePlan and the two allow-listed A01 tools. A real
runtime adapter can delegate model inference to LLMServe/llama.cpp while
reusing this contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


ALLOWED_TOOLS = {"lookup_model", "write_report"}
MAX_TOOL_CALLS = 2


@dataclass(frozen=True)
class A01Context:
    workspace: Path
    model: dict[str, Any]
    runtime: dict[str, Any]
    hardware: dict[str, Any]


def validate_runtime_plan(plan: dict[str, Any]) -> None:
    """Reject incomplete or unauthorized execution plans before inference."""
    if not plan.get("execution_authorized"):
        raise PermissionError("A01 execution requires explicit authorization")
    for section in ("model", "runtime", "hardware"):
        if not isinstance(plan.get(section), dict) or not plan[section]:
            raise ValueError(f"runtime plan requires non-empty {section}")
    if plan.get("tool_names") is not None:
        unknown = set(plan["tool_names"]) - ALLOWED_TOOLS
        if unknown:
            raise PermissionError(f"unauthorized A01 tools: {sorted(unknown)}")


def safe_workspace_path(workspace: Path, requested: str) -> Path:
    """Resolve an artifact path and prevent workspace escape."""
    root = workspace.resolve()
    candidate = (root / requested).resolve()
    if candidate != root and root not in candidate.parents:
        raise PermissionError("artifact path escapes A01 workspace")
    return candidate


def run_a01_tools(
    ctx: A01Context,
    lookup_model: Callable[[str], dict[str, str]],
    write_report: Callable[[str, str], str],
) -> tuple[dict[str, str], str]:
    """Execute exactly A01's two registered operations under the tool budget."""
    model = lookup_model("demo-2")
    if model.get("name") != "Beta":
        raise AssertionError("A01 lookup did not return the expected model")
    report = safe_workspace_path(ctx.workspace, "report.txt")
    artifact = write_report(str(report), model["name"])
    if Path(artifact).resolve() != report:
        raise AssertionError("writer returned an unexpected artifact path")
    if "Beta" not in report.read_text(encoding="utf-8"):
        raise AssertionError("A01 artifact does not contain Beta")
    return model, str(report)


__all__ = ["A01Context", "ALLOWED_TOOLS", "MAX_TOOL_CALLS", "validate_runtime_plan", "safe_workspace_path", "run_a01_tools"]
