#!/usr/bin/env python3
"""Valida y registra una medición real de inferencia.

Este script no ejecuta un modelo: recibe el resultado de una ejecución real y
lo convierte en un registro con un contrato estable. Separar la ejecución del
registro permite que cada runtime tenga su propio adaptador sin duplicar la
lógica de validación.

Para un lector con conocimientos básicos: una medición es una fila que dice
qué modelo se probó, en qué máquina y runtime, con qué configuración y cuántos
tokens por segundo se observaron realmente.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

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


def record_measurement(data: dict[str, Any], measured_at: str | None = None) -> dict[str, Any]:
    """Valida una medición y la devuelve marcada inequívocamente como real.

    No se aceptan valores vacíos ni negativos. ``measurement_type`` siempre es
    ``measured`` porque esta función está destinada exclusivamente a datos
    obtenidos de una ejecución real; las estimaciones deben seguir otro flujo.
    """
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

    result = dict(data)
    result["tokens_per_second"] = tokens_per_second
    result["context_tokens"] = context_tokens
    result["measurement_type"] = "measured"
    result["measured_at"] = measured_at or datetime.now(timezone.utc).isoformat()
    return result
