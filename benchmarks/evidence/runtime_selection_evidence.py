#!/usr/bin/env python3
"""Close the measured-performance feedback loop into runtime selection.

This is an evidence adapter, not a benchmark executor. It consumes a canonical
A01 result produced by a real runtime and creates a selector-compatible feedback
record. Estimated/reported/measured/verified remain distinct states.
"""
from __future__ import annotations

from typing import Any


ALLOWED_EVIDENCE = {"estimated", "reported", "measured", "verified"}


def build_runtime_feedback(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") or {}
    evidence_type = evidence.get("evidence_type")
    if evidence_type not in ALLOWED_EVIDENCE:
        raise ValueError("invalid evidence_type")
    if evidence_type == "verified":
        raise ValueError("verified evidence requires an independent verifier")

    agentic = result.get("agentic") or {}
    metrics = agentic.get("metrics") or {}
    runtime = agentic.get("runtime") or {}
    model = result.get("model") or {}
    hardware = result.get("hardware") or {}

    measured_tps = metrics.get("measured_tps")
    wall_seconds = metrics.get("runtime_wall_seconds")
    execution_id = evidence.get("execution_id") or agentic.get("execution_id")
    if evidence_type == "measured" and not execution_id:
        raise ValueError("measured evidence requires execution_id")

    return {
        "schema_version": "1.0",
        "feedback_type": "runtime-measurement",
        "evidence_type": evidence_type,
        "execution_id": execution_id,
        "model_id": model.get("id") or model.get("name"),
        "model_revision": model.get("revision"),
        "runtime": runtime.get("name"),
        "hardware": hardware,
        "metrics": {
            "measured_tps": measured_tps,
            "runtime_wall_seconds": wall_seconds,
            "tool_calls": metrics.get("tool_calls"),
            "tool_errors": metrics.get("tool_errors"),
            "recovery_count": metrics.get("recovery_count"),
        },
        "provenance": {
            "source": evidence.get("source"),
            "measured_at": evidence.get("measured_at"),
        },
        "selector_feedback": {
            "usable_for_runtime_comparison": evidence_type == "measured",
            "usable_as_verified_claim": False,
            "replace_estimate": evidence_type == "measured" and measured_tps is not None,
        },
    }


__all__ = ["build_runtime_feedback"]
