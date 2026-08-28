#!/usr/bin/env python3
"""Build the canonical LEONES ODS/Magnitude decision envelope.

This module is deliberately declarative: external fit signals never become
local measurements. LLMFit remains estimate-only. The LEONES selector remains
the authority for the final decision.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _source(
    payload: dict[str, Any] | None,
    *,
    available: bool,
    evidence_type: str = "unknown",
    estimate_only: bool = True,
) -> dict[str, Any]:
    payload = payload or {}
    return {
        "available": available,
        "product": payload.get("product"),
        "version": payload.get("version"),
        "revision": payload.get("revision"),
        "observed_at": payload.get("observed_at"),
        "evidence_type": evidence_type,
        "estimate_only": estimate_only,
    }


def build_decision(
    *,
    workload: dict[str, Any],
    hardware: dict[str, Any],
    runtime: dict[str, Any],
    selector_status: str,
    model_id: str | None,
    basis: list[str],
    ods_magnitude: dict[str, Any] | None = None,
    llmfit: dict[str, Any] | None = None,
    benchmark_required: bool = True,
    measured_performance_used: bool = False,
    measured_execution_id: str | None = None,
    candidates: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return one machine-readable decision without inventing measurements."""
    if selector_status not in {"REJECTED", "CANDIDATE", "SELECTED", "BENCHMARK_REQUIRED"}:
        raise ValueError(f"invalid selector_status: {selector_status}")
    if measured_performance_used and not measured_execution_id:
        raise ValueError("measured performance requires an execution_id")
    if measured_performance_used and not selector_status:
        raise ValueError("selector decision is required")

    decision = {
        "schema": "leones-ods-magnitude-decision.v1",
        "decision_id": f"decision-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workload": workload,
        "hardware": hardware,
        "runtime": runtime,
        "sources": {
            "ods_magnitude": _source(
                ods_magnitude,
                available=ods_magnitude is not None,
                evidence_type=(ods_magnitude or {}).get("evidence_type", "unknown"),
                estimate_only=(ods_magnitude or {}).get("estimate_only", True),
            ),
            "llmfit": _source(
                llmfit,
                available=llmfit is not None,
                evidence_type="reported" if llmfit is not None else "unknown",
                estimate_only=True,
            ),
        },
        "candidates": candidates or [],
        "decision": {
            "status": selector_status,
            "model_id": model_id,
            "basis": basis,
            "benchmark_required": benchmark_required,
            "measured_performance_used": measured_performance_used,
            "measured_execution_id": measured_execution_id,
        },
    }
    return decision


if __name__ == "__main__":
    raise SystemExit("library module; use build_decision()")
