#!/usr/bin/env python3
"""Valida que una medición pueda entrar en el flujo empírico de Atlas.

Una medición solo se promociona si está marcada como ``measured`` y contiene
la identidad mínima del modelo, hardware y runtime. El objetivo es impedir
que una estimación, un registro incompleto o una medición de otra máquina
contamine la evidencia empírica.
"""
from __future__ import annotations

from typing import Any

REQUIRED_IDENTITY = ("model", "hardware", "runtime", "tokens_per_second", "measurement_type")


def validate_measured_benchmark(measurement: dict[str, Any]) -> dict[str, Any]:
    """Devuelve una copia validada o lanza ``ValueError``.

    No modifica la medición ni convierte estimaciones en mediciones. La
    promoción posterior debe conservar exactamente el registro validado.
    """
    missing = [key for key in REQUIRED_IDENTITY if key not in measurement]
    if missing:
        raise ValueError(f"missing benchmark identity fields: {', '.join(missing)}")
    if measurement["measurement_type"] != "measured":
        raise ValueError("only measured benchmarks can be promoted")
    if not measurement["model"] or not measurement["hardware"] or not measurement["runtime"]:
        raise ValueError("model, hardware and runtime must be non-empty")
    try:
        value = float(measurement["tokens_per_second"])
    except (TypeError, ValueError) as exc:
        raise ValueError("tokens_per_second must be numeric") from exc
    if value < 0:
        raise ValueError("tokens_per_second cannot be negative")

    result = dict(measurement)
    result["tokens_per_second"] = value
    return result
