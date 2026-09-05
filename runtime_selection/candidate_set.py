"""RC3 candidate-set.v1 construction.

A candidate set is a normalized proposal layer between discovery and user
selection. It is source-agnostic: it does not know or infer which selector
produced a candidate. It never measures performance and never authorizes
execution.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "candidate-set.v1"


def build_candidate_set(
    hardware: dict[str, Any],
    raw_candidates: list[dict[str, Any]],
    *,
    source: str = "external",
    source_version: str | None = None,
) -> dict[str, Any]:
    """Build a deterministic, provenance-preserving RC3 candidate set."""
    candidates: list[dict[str, Any]] = []
    for position, item in enumerate(raw_candidates, 1):
        model_id = item.get("model_id") or item.get("id")
        if not model_id:
            continue
        candidates.append(
            {
                "model_id": model_id,
                "name": item.get("name") or model_id,
                "revision": item.get("revision"),
                "rank": item.get("rank", position),
                "quantization": item.get("quantization"),
                "parameters": item.get("parameters"),
                "active_parameters": item.get("active_parameters"),
                "runtime": item.get("runtime"),
                "source": item.get("source") or source,
                "source_version": item.get("source_version", source_version),
                "evidence_level": item.get("evidence_level", "estimated"),
                "selection_status": "CANDIDATE",
                "execution_authorized": False,
                "measurement_required": True,
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "hardware": hardware,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "selection": {
            "user_choice_required": True,
            "selected_model_id": None,
            "execution_authorized": False,
        },
        "measurement": {"measured": False, "runtime_benchmark_required": True},
    }


def validate_candidate_set(payload: dict[str, Any]) -> None:
    """Validate the boundary between proposals and execution."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported candidate-set schema")
    if not isinstance(payload.get("candidates"), list):
        raise ValueError("candidate-set candidates must be a list")
    if payload.get("selection", {}).get("execution_authorized") is not False:
        raise ValueError("candidate-set cannot authorize execution")
    if payload.get("measurement", {}).get("measured") is not False:
        raise ValueError("candidate-set cannot contain measurements")

    forbidden = {
        "tokens_per_second",
        "measured_tps",
        "benchmark_result",
        "command",
        "argv",
        "execution_id",
        "latency_ms",
    }
    for candidate in payload["candidates"]:
        leaked = forbidden.intersection(candidate)
        if leaked:
            raise ValueError(
                f"candidate contains execution/measurement fields: {sorted(leaked)}"
            )
