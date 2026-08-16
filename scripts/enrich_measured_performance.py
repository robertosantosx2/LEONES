#!/usr/bin/env python3
"""Añade CABE/RULA a una medición real sin perder el dato original.

El proyecto mantiene una distinción importante: ``tokens_per_second`` es la
medición y ``performance_class`` es una interpretación derivada. Este módulo
solo hace esa unión y rechaza datos que no estén marcados como medidos.
"""
from __future__ import annotations

from typing import Any

from classify_performance import classify_measurement


def enrich_measured_performance(measurement: dict[str, Any]) -> dict[str, Any]:
    """Clasifica una medición marcada como ``measured``.

    Las estimaciones no pasan por este camino porque CABE/RULA debe poder
    distinguirse de los valores calculados o previstos.
    """
    if measurement.get("measurement_type") != "measured":
        raise ValueError("CABE/RULA requires a real measurement")

    result = dict(measurement)
    result.update(classify_measurement(result["tokens_per_second"]))
    return result
