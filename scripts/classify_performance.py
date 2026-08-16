#!/usr/bin/env python3
"""Punto de entrada único para clasificar mediciones de rendimiento.

Este módulo conecta la normalización con el clasificador CABE/RULA. La idea es
que los pipelines de LEONES no tengan que copiar las reglas en varios sitios.
Si mañana cambia una frontera, se cambia aquí y en el contrato, no en cada
pipeline.
"""
from __future__ import annotations

from typing import Any

from classify_cabe_rula import classify_tokens_per_second
from normalize_cabe_rula_measurement import normalize_measurement


def classify_measurement(value: Any) -> dict[str, float | str]:
    """Normaliza una medición y devuelve valor + clasificación.

    ``tokens_per_second`` conserva el valor medido; ``performance_class``
    contiene solamente la etiqueta derivada de ese valor.
    """
    tokens_per_second = normalize_measurement(value)
    return {
        "tokens_per_second": tokens_per_second,
        "performance_class": classify_tokens_per_second(tokens_per_second),
    }
