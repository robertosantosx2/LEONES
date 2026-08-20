#!/usr/bin/env python3
"""Canonical gate between model selection and runtime execution.

Only candidates produced by the LEONES model selector may enter a runtime.
The gate resolves a runtime/quantization pair and refuses execution when the
selection is incomplete, rejected, or requires a benchmark before claims can
be made. It does not execute models and does not turn estimates into measures.
"""
from __future__ import annotations

from typing import Any

ALLOWED_FOR_EXECUTION = {"TOP_N"}


def resolve_runtime(candidate: dict[str, Any], *, available_runtimes: set[str] | None = None) -> dict[str, Any]:
    status = str(candidate.get("selection_status") or "")
    if status not in ALLOWED_FOR_EXECUTION:
        raise ValueError(f"candidate is not executable from selection state: {status or 'missing'}")

    model_id = candidate.get("model_id") or candidate.get("model_name")
    runtime = candidate.get("runtime")
    quantization = candidate.get("quantization")
    if not model_id:
        raise ValueError("selected candidate has no model identity")
    if not runtime:
        raise ValueError("selected candidate has no runtime")
    if not quantization:
        raise ValueError("selected candidate has no quantization")
    if available_runtimes is not None and runtime not in available_runtimes:
        raise ValueError(f"runtime is unavailable: {runtime}")

    return {
        "schema_version": "1.0",
        "model_id": model_id,
        "variant": candidate.get("variant"),
        "runtime": runtime,
        "quantization": quantization,
        "selection_status": status,
        "selection_rank": candidate.get("rank"),
        "fit_score": candidate.get("fit_score"),
        "evidence_level": candidate.get("evidence_level"),
        "execution_authorized": True,
        "measurement_required": True,
        "estimated_tps": (candidate.get("llmfit") or {}).get("estimated_tps"),
        "measured_tps": None,
    }


def gate_selection(selection: dict[str, Any], *, available_runtimes: set[str] | None = None) -> dict[str, Any]:
    """Convert a selector result into executable runtime plans."""
    plans: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for candidate in selection.get("candidates", []):
        try:
            plans.append(resolve_runtime(candidate, available_runtimes=available_runtimes))
        except ValueError as exc:
            blocked.append({
                "model_id": candidate.get("model_id") or candidate.get("model_name"),
                "selection_status": candidate.get("selection_status"),
                "reason": str(exc),
            })
    return {
        "schema_version": "1.0",
        "gate": "LEONES-runtime-selection-gate",
        "execution_plans": plans,
        "blocked": blocked,
        "counts": {"plans": len(plans), "blocked": len(blocked)},
    }
