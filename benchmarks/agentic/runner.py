#!/usr/bin/env python3
"""Deterministic execution contract for Agentic Benchmark V1."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable
import json
import time
import uuid

from runtime_selection.adapters import ExecutionSpec, RuntimeAdapter
from runtime_selection.contract import RuntimeSelectionPlan, validate_plan

EVENT_TYPES = {"model", "tool_call", "tool_result", "error", "recovery", "artifact", "grader", "other"}
EVIDENCE_TYPES = {"estimated", "reported", "measured", "verified"}


@dataclass
class Event:
    type: str
    timestamp: str
    name: str | None = None
    duration_seconds: float | None = None
    status: str | None = None
    details: dict[str, Any] | None = None


class Trace:
    """Append-only execution trace with a schema-aligned vocabulary."""

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


def prepare_selected_runtime(
    trace: Trace,
    plan: RuntimeSelectionPlan,
    adapter: RuntimeAdapter,
) -> ExecutionSpec:
    """Materialize a validated selection plan through the existing runner boundary.

    Selection remains declarative: no command, executable or measurement is
    added here. The trusted adapter is the only component allowed to translate
    the plan into an execution specification.
    """
    validate_plan(plan.to_dict())
    if adapter.adapter_id != plan.adapter_id:
        raise ValueError(
            f"adapter mismatch: plan={plan.adapter_id!r}, adapter={adapter.adapter_id!r}"
        )

    started = time.monotonic()
    trace.add(
        "model",
        name=plan.model_ref,
        status="selected",
        details={"runtime_id": plan.runtime_id, "adapter_id": plan.adapter_id},
    )
    try:
        spec = adapter.prepare(plan)
    except Exception as exc:
        trace.add(
            "error",
            name=plan.runtime_id,
            duration_seconds=time.monotonic() - started,
            status="selection_error",
            details={"error_type": type(exc).__name__},
        )
        raise

    trace.add(
        "model",
        name=plan.model_ref,
        duration_seconds=time.monotonic() - started,
        status="prepared",
        details={
            "runtime_id": spec.runtime_id,
            "adapter_id": spec.adapter_id,
            "execution_metadata": spec.execution_metadata,
        },
    )
    return spec


def execute_selected_runtime(
    trace: Trace,
    plan: RuntimeSelectionPlan,
    adapter: RuntimeAdapter,
    executor: Callable[[ExecutionSpec], Any],
) -> Any:
    """Run a selected runtime without creating a second execution architecture."""
    spec = prepare_selected_runtime(trace, plan, adapter)
    started = time.monotonic()
    try:
        result = executor(spec)
    except Exception as exc:
        trace.add(
            "error",
            name=spec.runtime_id,
            duration_seconds=time.monotonic() - started,
            status="execution_error",
            details={"error_type": type(exc).__name__},
        )
        raise

    trace.add(
        "model",
        name=spec.model_ref,
        duration_seconds=time.monotonic() - started,
        status="completed",
        details={"runtime_id": spec.runtime_id, "adapter_id": spec.adapter_id},
    )
    return result


def execute_tool(
    trace: Trace,
    name: str,
    fn: Callable[..., Any],
    *,
    tool_calls_so_far: int = 0,
    max_tool_calls: int = 10,
    **kwargs: Any,
) -> Any:
    """Run one approved tool and record invocation plus result."""
    if tool_calls_so_far >= max_tool_calls:
        trace.add("error", name=name, status="budget_exceeded", details={"max_tool_calls": max_tool_calls})
        raise RuntimeError("tool-call budget exceeded")

    started = time.monotonic()
    trace.add("tool_call", name=name, status="started", details={"argument_keys": sorted(kwargs)})
    try:
        result = fn(**kwargs)
    except Exception as exc:
        elapsed = time.monotonic() - started
        trace.add("error", name=name, duration_seconds=elapsed, status="error", details={"error_type": type(exc).__name__})
        raise

    elapsed = time.monotonic() - started
    trace.add("tool_result", name=name, duration_seconds=elapsed, status="ok", details={"result_type": type(result).__name__})
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
    evidence_type: str = "reported",
    evidence_source: str = "agentic-runner",
) -> dict[str, Any]:
    """Build the canonical result while keeping status and evidence separate.

    ``status`` describes the result lifecycle; ``evidence_type`` describes
    provenance. A runner may emit ``measured`` only when its caller has actual
    execution evidence. Nothing is promoted to ``verified`` automatically.
    """
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError(f"unsupported evidence_type: {evidence_type}")
    if evidence_type == "verified":
        raise ValueError("verified evidence requires an explicit independent verifier")

    execution_id = str(uuid.uuid4())
    evidence: dict[str, Any] = {
        "evidence_type": evidence_type,
        "source": evidence_source,
    }
    if evidence_type == "measured":
        evidence["execution_id"] = execution_id
        evidence["measured_at"] = datetime.now(timezone.utc).isoformat()

    return {
        "schema_version": "1.1",
        "status": "reported",
        "evidence": evidence,
        "hardware": hardware,
        "model": model,
        "inference": inference,
        "lotb": {},
        "agentic": {
            "benchmark_id": config.benchmark_id,
            "benchmark_version": config.benchmark_version,
            "task_id": config.task_id,
            "task_version": config.task_version,
            "execution_id": execution_id,
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
