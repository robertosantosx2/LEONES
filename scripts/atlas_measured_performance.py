#!/usr/bin/env python3
"""Integra mediciones reales de rendimiento en un feed de Atlas.

La matriz de hardware puede contener estimaciones y el benchmark puede
contener mediciones. Este adaptador conserva esa diferencia: solo incorpora
registros cuyo ``measurement_type`` sea ``measured`` y une la medición por
``model_id`` + hardware + runtime cuando esos datos están disponibles.

Para un lector con conocimientos básicos: el script no recalcula tok/s ni
convierte una predicción en un hecho. Simplemente añade al registro Atlas la
última evidencia medida que coincide con el mismo modelo, máquina y runtime.
"""
from __future__ import annotations

from typing import Any

from enrich_measured_performance import enrich_measured_performance


def integrate_measurements(rows: list[dict[str, Any]], measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Añade la última medición compatible a cada fila Atlas.

    La coincidencia prioriza ``model_id`` cuando existe y exige que hardware y
    runtime coincidan. Si no hay una medición compatible, la fila queda intacta.
    """
    valid = [m for m in measurements if m.get("measurement_type") == "measured"]
    result: list[dict[str, Any]] = []

    for row in rows:
        matches = [
            m for m in valid
            if (not row.get("model_id") or m.get("model_id") == row.get("model_id"))
            and m.get("hardware") == row.get("hardware")
            and m.get("runtime") == row.get("runtime")
        ]
        output = dict(row)
        if matches:
            measured = enrich_measured_performance(matches[-1])
            output["measured_tokens_per_second"] = measured["tokens_per_second"]
            output["measured_performance_class"] = measured["performance_class"]
            output["measurement_type"] = "measured"
            output["measured_at"] = measured["measured_at"]
        result.append(output)

    return result
