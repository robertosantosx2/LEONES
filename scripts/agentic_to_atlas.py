#!/usr/bin/env python3
"""Bridge measured Agentic Benchmark results into the Atlas performance feed.

This bridge deliberately accepts only evidence produced by a concrete
execution. It does not turn benchmark scores into throughput measurements and
never promotes evidence to ``verified``.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from scripts.validate_evidence import validate_evidence


def agentic_to_atlas(result: dict[str, Any]) -> dict[str, Any]:
    evidence = result.get("evidence") or {}
    validate_evidence(evidence)
    if evidence.get("evidence_type") != "measured":
        raise ValueError("only measured Agentic Benchmark results may enter the measured Atlas feed")

    agentic = result.get("agentic") or {}
    model = result.get("model") or {}
    inference = result.get("inference") or {}
    metrics = agentic.get("metrics") or {}
    execution_id = evidence.get("execution_id") or agentic.get("execution_id")
    if not execution_id:
        raise ValueError("Agentic result has no execution identity")

    measured_at = evidence.get("measured_at") or datetime.now(timezone.utc).isoformat()
    outcome = agentic.get("outcome") or {}
    return {
        "model_id": model.get("model_id") or model.get("name"),
        "model": model.get("name"),
        "variant": model.get("variant") or model.get("format") or "agentic",
        "runtime": (agentic.get("runtime") or {}).get("name") or "unknown",
        "hardware": (result.get("hardware") or {}).get("profile") or "unknown",
        "workload": agentic.get("benchmark_id"),
        "benchmark_id": agentic.get("benchmark_id"),
        "benchmark_version": agentic.get("benchmark_version"),
        "task_id": agentic.get("task_id"),
        "task_version": agentic.get("task_version"),
        "agentic_outcome": outcome.get("status"),
        "agentic_score": outcome.get("score"),
        "elapsed_seconds": metrics.get("elapsed_seconds") or inference.get("elapsed_seconds"),
        "tool_calls": metrics.get("tool_calls"),
        "tool_errors": metrics.get("tool_errors"),
        "recovery_count": metrics.get("recovery_count"),
        "tokens_per_second": inference.get("generation_tokens_per_second"),
        "execution_id": execution_id,
        "evidence_type": "measured",
        "measured_at": measured_at,
        "source": "LEONES-Agentic",
    }
