#!/usr/bin/env python3
"""Record an observed benchmark measurement.

This module validates the small legacy record shape used by the active
llama.cpp runner. It does not execute commands or publish results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from scripts.validate_evidence import validate_evidence

REQUIRED = (
    "model",
    "variant",
    "runtime",
    "hardware",
    "workload",
    "quantization",
    "context_tokens",
    "tokens_per_second",
)


def record_measurement(
    data: dict[str, Any], measured_at: str | None = None
) -> dict[str, Any]:
    """Validate and mark a real-inference record as measured."""
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    try:
        tokens_per_second = float(data["tokens_per_second"])
        context_tokens = int(data["context_tokens"])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "tokens_per_second and context_tokens must be numeric"
        ) from exc

    if tokens_per_second < 0:
        raise ValueError("tokens_per_second cannot be negative")
    if context_tokens < 0:
        raise ValueError("context_tokens cannot be negative")

    timestamp = measured_at or datetime.now(timezone.utc).isoformat()
    result = dict(data)
    result["tokens_per_second"] = tokens_per_second
    result["context_tokens"] = context_tokens
    result["execution_id"] = result.get("execution_id") or str(uuid4())
    result["measurement_type"] = "measured"
    result["measurement_kind"] = "real"
    result["evidence_type"] = "measured"
    result["measured_at"] = timestamp
    validate_evidence(
        {
            "evidence_type": "measured",
            "execution_id": result["execution_id"],
            "measured_at": timestamp,
            "measurement_kind": result["measurement_kind"],
        }
    )
    return result
