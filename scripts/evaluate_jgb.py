#!/usr/bin/env python3
"""Deriva una clase JGB a partir de evidencias explícitas.

El evaluador es deliberadamente conservador: una dimensión solo se considera
resuelta cuando trae un nivel válido, un estado de evidencia aceptable y al
menos una fuente. Si falta cualquiera de esos elementos, la dimensión queda
``unknown`` y la clase global no se deriva.
"""
from __future__ import annotations

from typing import Any

DIMENSIONS = ("access", "model_control", "data_control", "autonomy", "trust")
VALID_STATUSES = {"verified", "provisional", "supported", "unknown", "disputed"}


def evaluate_jgb(evidence: dict[str, Any]) -> dict[str, Any]:
    """Devuelve dimensiones JGB, clase, estado y dimensiones no resueltas.

    La función conserva las evidencias recibidas y no inventa valores. La
    clase global solo se calcula cuando las cinco dimensiones están resueltas
    con evidencia trazable. ``provisional`` no se promociona a ``verified``.
    """
    dimensions: dict[str, Any] = {}
    unresolved: list[str] = []

    for dimension in DIMENSIONS:
        item = evidence.get(dimension)
        if not isinstance(item, dict):
            dimensions[dimension] = {"level": None, "status": "unknown", "sources": []}
            unresolved.append(dimension)
            continue

        level = item.get("level")
        status = item.get("status", "unknown")
        sources = item.get("sources", [])
        valid_level = isinstance(level, int) and 0 <= level <= 5
        valid_sources = isinstance(sources, list) and len(sources) > 0
        valid_status = status in VALID_STATUSES
        resolved = valid_level and valid_sources and valid_status and status in {"verified", "supported"}

        dimensions[dimension] = {
            "level": level if valid_level else None,
            "status": status if valid_status else "unknown",
            "sources": sources if isinstance(sources, list) else [],
        }
        if not resolved:
            unresolved.append(dimension)

    levels = [dimensions[d]["level"] for d in DIMENSIONS]
    jgb_class = min(levels) if not unresolved else None
    return {
        "dimensions": dimensions,
        "jgb_class": jgb_class,
        "status": "supported" if not unresolved else "unknown",
        "unresolved": unresolved,
    }
