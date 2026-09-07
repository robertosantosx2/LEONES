#!/usr/bin/env python3
"""Generate LEONES master CPU/RAM/GPU -> AA model matrices.

The JSON snapshot is the source for the inventory and AA scores. Exact
production fit/quantization remains delegated to LLMFit.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "master_hardware_model_matrix.v1.json"
OUT = ROOT / "docs" / "MASTER-HARDWARE-MODEL-MATRIX.generated.md"


def fit_q4(model: dict, vram: float, ram: float) -> bool:
    p = float(model["params_b"])
    # Reference approximation documented by LLMFit: 0.5 GB/parameter,
    # with 1.1x VRAM and 1.2x RAM overhead. Production uses LLMFit itself.
    return p * 0.5 * 1.1 <= vram or p * 0.5 * 1.2 <= ram


def select(models: list[dict], vram: float, ram: float) -> dict | None:
    eligible = [m for m in models if fit_q4(m, vram, ram)]
    if not eligible:
        return None
    return max(eligible, key=lambda m: float(m["aa_score"]))


def render_table(gpus: list[dict], models: list[dict], ram_values: list[int]) -> str:
    head = "| GPU (orden de potencia de referencia) | VRAM | " + " | ".join(f"{r} GB RAM" for r in ram_values) + " |"
    sep = "|---|---:|" + "---|" * len(ram_values)
    rows = [head, sep]
    for gpu in sorted(gpus, key=lambda x: x["rank"]):
        cells = []
        for ram in ram_values:
            m = select(models, gpu["vram_gb"], ram)
            cells.append("—" if m is None else f'{m["name"]} · AA {m["aa_score"]}')
        rows.append(f'| {gpu["rank"]}. {gpu["model"]} ({gpu["vendor"]}) | {gpu["vram_gb"]} GB | ' + " | ".join(cells) + " |")
    return "\n".join(rows)


def main() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    rams = data["ram_gb"]
    parts = [
        "# LEONES — Cuadros maestros hardware → LLM (generado)",
        "",
        f'**Contrato:** `{data["schema"]}`',
        f'**Snapshot:** {data["snapshot_date"]}',
        f'**Artificial Analysis:** {data["aa_index"]}',
        "",
        "La selección es `LLMFit → elegibles → máximo Artificial Analysis Intelligence Index`.",
        "Las tres familias CPU conservan el mismo cruce intelectual; el CPU se usa después para rendimiento y benchmark físico.",
        "",
    ]
    for cpu in data["cpu_tiers"]:
        parts += [f'## {cpu["label"]}', "", render_table(data["gpu_inventory"], data["model_catalog"], rams), ""]
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
