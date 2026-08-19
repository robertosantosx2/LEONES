#!/usr/bin/env python3
"""Small, deterministic execution contract for Agentic Benchmark V1.

The runner only executes explicitly registered tools. Model output must be
translated into an approved tool call by an adapter; arbitrary commands are
never executed by this module.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import json
import time
import uuid

EVENT_TYPES = {"model", "tool_call", "tool_result", "error", "recovery", "artifact", "grader", "other"}


@dataclass
class Event:
    type: str
    timestamp: str
    name: str | None = None
    duration_seconds: float | None = None
    status: str | None = None
    details: dict[str, Any] | None = None


class Trace:
    """Append-only execution trace with a small, schema-aligned vocabulary."""

    def __init__(self) -> None:
        self.events: list[Event] = []

    def add(self, event_type: str, **kwargs: Any) -> None:
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unsupported event type: {event_type}")
        self.events.append(Event(type=event_type, timestamp=datetime.now(timezone.utc).isoformat(), **kwargs))


@dataclass(frozen=True)
class RunConfig:
    benchmark_id: str
    benchmark_version: str
    task_id: str
    task_version: str
    max_tool_calls: int = 10

    def __post_init__(self) -> None:
        if self.max_tool_calls < 1:
            raise ValueError("max_tool_calls must be >= 1")


def execute_tool(
    trace: Trace,
    name: str,
    fn: Callable[..., Any],
    *,
    tool_calls_so_far: int = 0,
    max_tool_calls: int = 10,
    **kwargs: Any,
) -> Any:
    """Run one approved tool and record both invocation and result.

    The caller supplies the adapter function; this function never interprets
    model text as executable code.
    """
    if tool_calls_so_far >= max_tool_calls:
        trace.add("error", name=name, status="budget_exceeded", details={"max_tool_calls": max_tool_calls})
        raise RuntimeError("tool-call budget exceeded")

    started = time.monotonic()
    trace.add("tool_call", name=name, status="started", details={"argument_keys": sorted(kwargs)})
    try:
        result = fn(**kwargs)
    except Exception as exc:
        elapsed = time.monotonic() - started
        trace.add(
            "error",
            name=name,
            duration_seconds=elapsed,
            status="error",
            details={"error_type": type(exc).__name__},
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
    """Build the canonical result without inventing missing measurements."""
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
    """Write UTF-8 JSON suitable for schema validation."""
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    print("Agentic Benchmark V1 runner library: use an explicit task adapter to execute runs.")
