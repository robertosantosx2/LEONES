#!/usr/bin/env python3
"""Valida y registra una medición real de inferencia.

La procedencia es explícita: ``estimated`` y ``reported`` nunca pasan por esta
función. Una medición exige una ejecución identificable y conserva por separado
la etiqueta histórica ``measurement_type`` para compatibilidad con Atlas.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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
    "execution_id",
)


def record_measurement(data: dict[str, Any], measured_at: str | None = None) -> dict[str, Any]:
    """Validate a real execution result and mark it as measured."""
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ValueError(f"missing required fields: {', '.join(missing)}")

    try:
        tokens_per_second = float(data["tokens_per_second"])
        context_tokens = int(data["context_tokens"])
    except (TypeError, ValueError) as exc:
        raise ValueError("tokens_per_second and context_tokens must be numeric") from exc

    if tokens_per_second < 0:
        raise ValueError("tokens_per_second cannot be negative")
    if context_tokens < 0:
        raise ValueError("context_tokens cannot be negative")

    timestamp = measured_at or datetime.now(timezone.utc).isoformat()
    result = dict(data)
    result["tokens_per_second"] = tokens_per_second
    result["context_tokens"] = context_tokens
    result["measurement_type"] = "measured"
    result["evidence_type"] = "measured"
    result["measured_at"] = timestamp
    validate_evidence({
        "evidence_type": "measured",
        "execution_id": result["execution_id"],
        "measured_at": timestamp,
    })
    return result
