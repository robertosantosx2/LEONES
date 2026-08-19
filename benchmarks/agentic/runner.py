#!/usr/bin/env python3
"""Minimal deterministic Agentic Benchmark V1 runner skeleton.

This runner intentionally does not execute arbitrary model-generated commands.
It provides the execution contract and trace format that real adapters can use.

The first implementation is deliberately conservative: tool adapters are
explicitly supplied by the caller and every event is recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Callable
import json
import time
import uuid


@dataclass
class Event:
    type: str
    timestamp: str
    name: str | None = None
    duration_seconds: float | None = None
    status: str | None = None
    details: dict[str, Any] | None = None


class Trace:
    """Append-only execution trace."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def add(self, event_type: str, **kwargs: Any) -> None:
        self.events.append(
            Event(
                type=event_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
                **kwargs,
            )
        )


@dataclass
class RunConfig:
    benchmark_id: str
    benchmark_version: str
    task_id: str
    task_version: str
    max_tool_calls: int = 10


def execute_tool(
    trace: Trace,
    name: str,
    fn: Callable[..., Any],
    **kwargs: Any,
) -> Any:
    """Execute one explicitly registered tool and record success/failure."""
    started = time.monotonic()
    trace.add("tool_call", name=name, details={"arguments": kwargs})
    try:
        result = fn(**kwargs)
    except Exception as exc:  # pragma: no cover - adapter-specific failures
        elapsed = time.monotonic() - started
        trace.add(
            "error",
            name=name,
            duration_seconds=elapsed,
            status="error",
            details={"error_type": type(exc).__name__, "message": str(exc)},
        )
        raise
    elapsed = time.monotonic() - started
    trace.add(
        "tool_result",
        name=name,
        duration_seconds=elapsed,
        status="ok",
        details={"result_type": type(result).__name__},
    )
    return result


def build_result(
    config: RunConfig,
    trace: Trace,
    *,
    model: dict[str, Any],
    hardware: dict[str, Any],
    inference: dict[str, Any],
    outcome: dict[str, Any],
    metrics: dict[str, Any],
    runtime: dict[str, str] | None = None,
    scaffold: dict[str, str] | None = None,
    environment: dict[str, str] | None = None,
    tools: list[dict[str, Any]] | None = None,
    grader: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the canonical LEONES result without inventing missing values."""
    return {
        "schema_version": "1.1",
        "status": "reported",
        "hardware": hardware,
        "model": model,
        "inference": inference,
        "lotb": {},
        "agentic": {
            "benchmark_id": config.benchmark_id,
            "benchmark_version": config.benchmark_version,
            "task_id": config.task_id,
            "task_version": config.task_version,
            "execution_id": str(uuid.uuid4()),
            "model_version": model.get("revision"),
            "runtime": runtime or {},
            "scaffold": scaffold or {},
            "environment": environment or {},
            "tools": tools or [],
            "outcome": outcome,
            "trajectory": [asdict(event) for event in trace.events],
            "metrics": metrics,
            "safety": {},
            "artifacts": [],
            "grader": grader or {},
        },
    }


def write_result(result: dict[str, Any], path: str) -> None:
    """Write UTF-8 JSON suitable for validation by the repository schema."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    print("Agentic Benchmark V1 runner library: use task adapters to execute runs.")
