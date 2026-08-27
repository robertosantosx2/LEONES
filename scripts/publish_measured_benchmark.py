#!/usr/bin/env python3
"""Publica una medición ya validada en un fichero JSONL de evidencia.

Este es el último paso del flujo de benchmark. Recibe un registro que ya ha
pasado por ``promote_measured_benchmark`` y lo añade como una línea al almacén
de evidencia. JSONL se usa porque cada medición queda como un registro
independiente y el fichero puede revisarse antes de incorporarlo a otros
artefactos de Atlas.

La función no ejecuta modelos ni recalcula resultados. Tampoco borra
mediciones anteriores: una medición nueva es nueva evidencia y conserva su
marca temporal.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    from scripts.promote_measured_benchmark import promote
except ModuleNotFoundError:  # ejecución directa
    from promote_measured_benchmark import promote


def publish(path: str | Path, measurement: dict[str, Any]) -> dict[str, Any]:
    """Valida, enriquece y añade una medición al fichero JSONL indicado."""
    promoted = promote(measurement)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(promoted, ensure_ascii=False, sort_keys=True) + "\n")
    return promoted
