#!/usr/bin/env python3
"""Enriquece un feed de Atlas con una evaluación JGB trazable.

Este pequeño adaptador une dos piezas del proyecto: el feed de modelos y el
motor de evaluación JGB. No decide qué significa "abierto" por su cuenta.
Recibe las cinco dimensiones y deja que ``evaluate_jgb`` aplique el contrato
común.

Para una persona que empieza a programar: un *feed* es simplemente una lista
de filas de modelos. El fichero JSON de evidencias contiene, para cada
``model_id``, la información que permite valorar esas cinco dimensiones.

La ausencia de una evidencia no se transforma en una suposición: se conserva
como ``unknown``. Esto es importante porque Atlas debe distinguir "no sabemos"
de "hemos comprobado que no cumple".
"""

from __future__ import annotations

import argparse
import csv
import json
from typing import Any

from evaluate_jgb import evaluate_jgb


def enrich(
    rows: list[dict[str, Any]], evidence_by_model: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    """Añade el resultado JGB a cada fila sin alterar sus demás métricas.

    ``model_id`` es la llave que une la fila del Atlas con sus evidencias.
    ``jgb_level`` queda vacío cuando no se puede calcular una clase completa;
    ``jgb_status`` explica si la evaluación está respaldada; y
    ``jgb_unresolved`` enumera las dimensiones que todavía necesitan evidencia.
    """
    enriched: list[dict[str, Any]] = []
    for row in rows:
        model_id = row.get("model_id", "")
        evidence = evidence_by_model.get(model_id, {})
        result = evaluate_jgb(evidence)

        output = dict(row)
        output["jgb_level"] = "" if result["jgb_class"] is None else result["jgb_class"]
        output["jgb_status"] = result["status"]
        output["jgb_unresolved"] = ";".join(result["unresolved"])
        enriched.append(output)

    return enriched


def main() -> None:
    """Lee CSV + JSON y escribe un nuevo CSV enriquecido.

    Los tres argumentos son rutas de ficheros. El original nunca se modifica:
    el resultado se escribe en ``--output`` para que el pipeline pueda revisar
    el artefacto antes de promocionarlo.
    """
    parser = argparse.ArgumentParser(description="Enriquece Atlas con JGB verificable")
    parser.add_argument("--input", required=True, help="CSV del feed Atlas")
    parser.add_argument(
        "--evidence", required=True, help="JSON de evidencias por model_id"
    )
    parser.add_argument("--output", required=True, help="CSV de salida enriquecido")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    with open(args.evidence, encoding="utf-8") as handle:
        evidence = json.load(handle)

    enriched = enrich(rows, evidence)
    fields = (
        list(enriched[0].keys())
        if enriched
        else ["model_id", "jgb_level", "jgb_status", "jgb_unresolved"]
    )

    with open(args.output, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(enriched)


if __name__ == "__main__":
    main()
