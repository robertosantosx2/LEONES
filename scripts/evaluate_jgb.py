#!/usr/bin/env python3
"""Deriva una clase JGB a partir de evidencias explícitas.

El script no intenta adivinar la apertura de un modelo. Cada dimensión solo
puede recibir una clase si existe evidencia suministrada por el pipeline.
Cuando falta evidencia, devuelve ``unknown`` para que la ausencia no se
convierta accidentalmente en una afirmación.
"""
from __future__ import annotations

from typing import Any

DIMENSIONS = ("access", "model_control", "data_control", "autonomy", "trust")


def evaluate_jgb(evidence: dict[str, Any]) -> dict[str, Any]:
    """Devuelve dimensiones JGB, confianza y estado de evidencia.

    La función conserva las evidencias recibidas y no inventa valores. La
    clase global solo se calcula cuando las cinco dimensiones están resueltas.
    """
    dimensions: dict[str, Any] = {}
    unresolved = []
    for dimension in DIMENSIONS:
        item = evidence.get(dimension)
        if not isinstance(item, dict) or item.get("level") is None:
            dimensions[dimension] = {"level": None, "status": "unknown"}
            unresolved.append(dimension)
        else:
            dimensions[dimension] = {
                "level": item["level"],
                "status": item.get("status", "supported"),
                "sources": item.get("sources", []),
            }

    # JGB se mantiene independiente de rendimiento, precio y fit_score.
    levels = [dimensions[d]["level"] for d in DIMENSIONS]
    jgb_class = None if unresolved else min(levels)
    return {
        "dimensions": dimensions,
        "jgb_class": jgb_class,
        "status": "unknown" if unresolved else "supported",
        "unresolved": unresolved,
    }
