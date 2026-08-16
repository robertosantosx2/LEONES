#!/usr/bin/env python3
"""Enriquece un feed Atlas con JGB derivado de evidencia explícita.

Este adaptador mantiene JGB separado de ``fit_score``. Solo copia una clase
cuando las cinco dimensiones tienen evidencia suficiente; en caso contrario
conserva ``unknown`` y deja constancia de las dimensiones pendientes.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from evaluate_jgb import evaluate_jgb


def enrich(rows: list[dict], evidence_by_model: dict[str, dict]) -> list[dict]:
    """Añade JGB sin modificar las demás métricas del recomendador."""
    out = []
    for row in rows:
        evidence = evidence_by_model.get(row.get("model_id", ""), {})
        result = evaluate_jgb(evidence)
        copy = dict(row)
        copy["jgb_level"] = "" if result["jgb_class"] is None else result["jgb_class"]
        copy["jgb_status"] = result["status"]
        copy["jgb_unresolved"] = ";".join(result["unresolved"])
        out.append(copy)
    return out


def main() -> None:
    """Enriquece CSV usando un JSON de evidencias por model_id."""
    import argparse
    p = argparse.ArgumentParser(description="Enriquece Atlas con JGB verificable")
    p.add_argument("--input", required=True)
    p.add_argument("--evidence", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    with open(args.input, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    with open(args.evidence, encoding="utf-8") as f:
        evidence = json.load(f)
    rows = enrich(rows, evidence)

    fields = list(rows[0].keys()) if rows else ["model_id", "jgb_level", "jgb_status", "jgb_unresolved"]
    with open(args.output, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
