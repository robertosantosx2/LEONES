"""Common runtime-benchmark.v1 bridge for every V1.1 adapter.

It accepts execution facts from a runner and refuses to manufacture measured
performance from estimates. The resulting record is suitable as the input
boundary to the existing evidence layer.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import uuid

SCHEMA_VERSION = "runtime-benchmark.v1"


def begin(plan: dict[str, Any], *, protocol: dict[str, Any] | None = None) -> dict[str, Any]:
    if plan.get("execution_authorized") is not True:
        raise ValueError("cannot benchmark an unauthorized runtime plan")
    runtime = plan.get("runtime") or {}
    return {
        "schema_version": SCHEMA_VERSION,
        "execution_id": str(uuid.uuid4()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "runtime": runtime.get("name"),
        "adapter": runtime.get("adapter"),
        "runtime_version": runtime.get("version"),
        "model": plan.get("model"),
        "model_id": plan.get("model_id"),
        "quantization": plan.get("quantization"),
        "hardware": plan.get("hardware") or {},
        "workload": plan.get("workload") or {},
        "protocol": protocol or {},
        "provenance": {"kind": "LEONES-runtime-execution", "estimated_tps": plan.get("estimated_tps")},
        "measured": None,
    }


def complete(record: dict[str, Any], measured: dict[str, Any]) -> dict[str, Any]:
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid runtime benchmark schema")
    if not isinstance(measured, dict) or not measured:
        raise ValueError("measured runtime facts are required")
    if "estimated_tps" in measured:
        raise ValueError("estimated_tps cannot be submitted as a measurement")
    if "measured_tps" in measured and measured["measured_tps"] is not None:
        if not isinstance(measured["measured_tps"], (int, float)) or measured["measured_tps"] < 0:
            raise ValueError("measured_tps must be a non-negative number")
    result = dict(record)
    result["measured"] = dict(measured)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["measurement_status"] = "measured"
    return result
