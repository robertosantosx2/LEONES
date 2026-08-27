#!/usr/bin/env python3
"""Calcula el ranking económico V1 de LEONES.

Este script es deliberadamente sencillo: toma recomendaciones que ya han pasado
la capa técnica, consulta precios observados y calcula cuánto resultado técnico
se obtiene por cada 100 EUR de hardware considerado.

IMPORTANTE PARA MANTENIMIENTO:
- JGB, rendimiento y precio son dimensiones distintas.
- Un precio ausente NO se estima.
- La V1 solo considera CPU + RAM cuando ambos precios están disponibles.
- CPU + RAM NO equivale al precio de un PC completo.

La documentación humana está en docs/completed/H03-ECONOMIC-RANKING.md.
"""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

# ROOT apunta a la raíz del repositorio aunque el script se ejecute desde otra
# carpeta. Así los workflows pueden invocarlo sin depender del directorio actual.
ROOT = Path(__file__).resolve().parents[1]
PRICES = ROOT / "data/hardware/hardware_prices.csv"
IN = ROOT / "data/prospection/atlas_recommendations.csv"
OUT = ROOT / "data/prospection/atlas_economic_ranking.csv"


def num(v):
    """Convierte un campo CSV a número.

    Los CSV suelen contener cadenas vacías. Devolver None permite distinguir
    «no tenemos el dato» de un valor numérico igual a cero.
    """
    try:
        return float(v) if v not in ("", None) else None
    except (ValueError, TypeError):
        return None


def cpu_family(hardware):
    """Extrae la familia i3/i5/i7/i9 de un identificador de hardware."""
    m = re.search(r"\b(i[3579])\b", hardware.lower())
    return m.group(1) if m else None


def median(vals):
    """Devuelve la mediana de una lista o None si está vacía.

    La mediana se usa para que una observación excepcionalmente alta o baja
    no domine por sí sola el coste representativo.
    """
    vals = sorted(vals)
    if not vals:
        return None
    n = len(vals)
    return vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2


def load(path):
    """Carga un CSV y devuelve sus filas como diccionarios."""
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def component_price(prices, component, family=None, capacity=None):
    """Busca el precio observado representativo de un componente.

    `family` sirve para distinguir, por ejemplo, Core i5 de Core i7.
    `capacity` se utiliza principalmente para RAM.
    Si no hay observaciones compatibles, devuelve None: nunca inventamos precio.
    """
    candidates = []
    for p in prices:
        if p.get("component_type") != component:
            continue
        if family and family.lower() not in (p.get("category") or "").lower():
            continue
        cap = num(p.get("capacity_gb"))
        if capacity is not None and cap != capacity:
            continue
        price = num(p.get("price_eur"))
        if price is not None and price > 0:
            candidates.append(price)
    return median(candidates)


def hardware_cost(prices, hardware, ram):
    """Calcula el coste V1 y declara si la cobertura es completa.

    V1 exige precio para CPU y RAM. Si falta una de las dos piezas, devolvemos
    `partial` y no fabricamos un coste total.
    """
    parts = {}
    cpu = cpu_family(hardware)
    if cpu:
        parts["cpu"] = component_price(prices, "cpu", cpu)
    parts["ram"] = component_price(prices, "ram", capacity=ram)

    known = [v for v in parts.values() if v is not None]
    coverage = "complete" if len(known) == 2 else "partial" if known else "unknown"
    return sum(known) if coverage == "complete" else None, coverage, parts


def economic_rank(rows, prices, hardware, ram):
    """Calcula y ordena las recomendaciones económicas.

    Primero se normaliza el rendimiento dentro del conjunto recibido. Después
    se combinan rendimiento, JGB y adecuación hardware según los pesos V1.
    Finalmente se divide la calidad técnica por el coste observado.
    """
    valid = []
    for r in rows:
        fit = num(r.get("fit_score"))
        tps = num(r.get("tokens_per_second"))
        jgb = num(r.get("jgb_level"))
        # Sin fit no podemos afirmar que el modelo sea adecuado al hardware.
        if fit is not None:
            valid.append((r, fit, tps, jgb))

    perf_vals = [x[2] for x in valid if x[2] is not None]
    pmin, pmax = (min(perf_vals), max(perf_vals)) if perf_vals else (None, None)
    hw_cost, cov, parts = hardware_cost(prices, hardware, ram)
    out = []

    for r, fit, tps, jgb in valid:
        # Si todos los rendimientos conocidos son iguales, todos reciben 100.
        # Si falta rendimiento, dejamos su componente como None y no fingimos
        # que sabemos cuánto rinde ese modelo.
        perf = (
            100
            if pmax == pmin and tps is not None
            else (
                100 * (tps - pmin) / (pmax - pmin)
                if tps is not None and pmax is not None and pmax > pmin
                else None
            )
        )
        jgb_score = (jgb / 5 * 100) if jgb is not None else None
        hardware_score = max(0, min(100, fit * 100))

        # Solo existe economic_score cuando tenemos coste completo de V1.
        if hw_cost is not None:
            quality = (
                0.35 * (perf if perf is not None else 0)
                + 0.25 * (jgb_score if jgb_score is not None else 0)
                + 0.40 * hardware_score
            )
            value = quality / (hw_cost / 100)
        else:
            value = None

        out.append(
            (
                value if value is not None else -1,
                r,
                perf,
                jgb_score,
                hardware_score,
                hw_cost,
                cov,
                parts,
            )
        )

    # Orden descendente: mayor valor económico primero.
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def main():
    """Lee argumentos, ejecuta el cálculo y escribe el CSV final."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default=str(IN))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--hardware", required=True)
    ap.add_argument("--ram", type=float, required=True)
    a = ap.parse_args()

    rows = load(Path(a.input))
    prices = load(PRICES)
    ranked = economic_rank(rows, prices, a.hardware, a.ram)

    # Incluso si no hay recomendaciones, conservamos la información de
    # cobertura del precio para que el resultado explique por qué está vacío.
    _, cov, _ = hardware_cost(prices, a.hardware, a.ram)

    fields = [
        "economic_rank",
        "model_id",
        "model_name",
        "hardware_id",
        "fit_score",
        "jgb_level",
        "jgb_score",
        "tokens_per_second",
        "performance_score",
        "hardware_score",
        "hardware_cost_eur",
        "price_coverage",
        "cpu_price_eur",
        "ram_price_eur",
        "economic_score",
        "price_basis",
    ]

    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i, (score, r, perf, jgb_score, hw_score, cost, cov, parts) in enumerate(
            ranked, 1
        ):
            w.writerow(
                {
                    "economic_rank": i,
                    "model_id": r.get("model_id", ""),
                    "model_name": r.get("model_name", ""),
                    "hardware_id": r.get("hardware_id", ""),
                    "fit_score": r.get("fit_score", ""),
                    "jgb_level": r.get("jgb_level", ""),
                    "jgb_score": f"{jgb_score:.2f}" if jgb_score is not None else "",
                    "tokens_per_second": r.get("tokens_per_second", ""),
                    "performance_score": f"{perf:.2f}" if perf is not None else "",
                    "hardware_score": f"{hw_score:.2f}",
                    "hardware_cost_eur": f"{cost:.2f}" if cost is not None else "",
                    "price_coverage": cov,
                    "cpu_price_eur": f"{parts['cpu']:.2f}"
                    if parts.get("cpu") is not None
                    else "",
                    "ram_price_eur": f"{parts['ram']:.2f}"
                    if parts.get("ram") is not None
                    else "",
                    "economic_score": f"{score:.6f}" if score >= 0 else "",
                    "price_basis": "median observed retail CPU+RAM; motherboard/storage/PSU/case/GPU excluded unless explicitly mapped",
                }
            )

    print(f"{len(ranked)} economic candidates -> {a.out}; price coverage={cov}")


if __name__ == "__main__":
    main()
