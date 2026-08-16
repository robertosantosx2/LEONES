#!/usr/bin/env python3
"""Prepara una medición validada para su publicación en Atlas.

La promoción es un paso explícito: primero valida la evidencia y después
produce un registro listo para el publicador. No escribe en Atlas directamente
ni sustituye datos existentes. Esto permite que el workflow de publicación
sea el único responsable de modificar el catálogo.
"""
from __future__ import annotations

from typing import Any

from enrich_measured_performance import enrich_measured_performance
from validate_measured_benchmark import validate_measured_benchmark


def promote(measurement: dict[str, Any]) -> dict[str, Any]:
    """Valida y enriquece una medición real para publicación."""
    validated = validate_measured_benchmark(measurement)
    return enrich_measured_performance(validated)
