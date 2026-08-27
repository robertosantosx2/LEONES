#!/usr/bin/env python3
"""Normaliza una medición de rendimiento para el contrato CABE/RULA.

La clasificación CABE/RULA solo tiene sentido si conservamos el dato que la
origina y el contexto en el que fue medido. Este módulo no intenta estimar
velocidad: recibe una observación ya obtenida y comprueba que sea utilizable.
"""

from __future__ import annotations

import math
from typing import Any


def normalize_measurement(value: Any) -> float:
    """Convierte tok/s a ``float`` y rechaza valores imposibles.

    Se aceptan números y cadenas como ``"7.5"``. No se aceptan valores vacíos,
    negativos, NaN ni infinito. Rechazar aquí evita que una mala fuente termine
    convertida silenciosamente en una categoría CABE/RULA.
    """
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("tokens_per_second debe ser numérico") from exc

    if not math.isfinite(result) or result < 0:
        raise ValueError("tokens_per_second debe ser finito y no negativo")
    return result


def build_performance_record(tokens_per_second: Any, **context: Any) -> dict[str, Any]:
    """Devuelve una observación lista para ser clasificada.

    El contexto se conserva tal cual para no perder información de procedencia.
    La función no asigna CABE/RULA: esa decisión pertenece al clasificador.
    """
    value = normalize_measurement(tokens_per_second)
    return {
        **context,
        "tokens_per_second": value,
    }
