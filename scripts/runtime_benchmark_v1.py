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
    if not runtime.get("name") or not runtime.get("adapter"):
        raise ValueError("benchmark plan must identify runtime and adapter")
    if not plan.get("model_id") or not plan.get("quantization"):
        raise ValueError("benchmark plan must identify model and quantization")
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
    numeric_measurements = [value for key, value in measured.items() if key != "estimated_tps" and isinstance(value, (int, float)) and not isinstance(value, bool)]
    if not numeric_measurements:
        raise ValueError("at least one numeric measured runtime fact is required")
    if "measured_tps" in measured and (not isinstance(measured["measured_tps"], (int, float)) or isinstance(measured["measured_tps"], bool) or measured["measured_tps"] < 0):
        raise ValueError("measured_tps must be a non-negative number")
    result = dict(record)
    result["measured"] = dict(measured)
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    result["measurement_status"] = "measured"
    return result
