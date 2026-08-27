#!/usr/bin/env python3
"""Construye la matriz CPU × RAM × NVIDIA para las recomendaciones Atlas.

Este script no mide rendimiento. Genera sistemáticamente muchos perfiles de
hardware y reutiliza el recomendador para saber qué modelos pasan sus filtros.

La matriz separa RAM del sistema y VRAM de la GPU. El contexto es una capacidad
del modelo y un objetivo del perfil, no una propiedad que crezca mágicamente
porque añadamos RAM al ordenador.

Documentación para humanos:
    docs/completed/H10-ATLAS-RECOMMENDER-PIPELINE.md
"""

from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GPU_FILE = ROOT / "data/hardware/nvidia_ai_gpus.csv"
OUT = ROOT / "data/prospection/atlas_hardware_matrix.csv"
RECOMMENDER = ROOT / "scripts/atlas_recommend_from_feed.py"
FEED = ROOT / "data/prospection/atlas_feed.csv"

# Son las familias de CPU que la matriz recorre automáticamente.
CPUS = [
    ("intel-i3", "Intel Core i3"),
    ("intel-i5", "Intel Core i5"),
    ("intel-i7", "Intel Core i7"),
    ("intel-i9", "Intel Core i9"),
    ("amd-ryzen3", "AMD Ryzen 3"),
    ("amd-ryzen5", "AMD Ryzen 5"),
    ("amd-ryzen7", "AMD Ryzen 7"),
    ("amd-ryzen9", "AMD Ryzen 9"),
]

# La RAM se mantiene como dimensión independiente de la VRAM.
RAMS = [2, 4, 8, 16, 32, 64, 128]

# Contrato del CSV de salida. Los consumidores esperan estas columnas.
FIELDS = [
    "cpu_family",
    "cpu_name",
    "ram_gb",
    "gpu_id",
    "gpu_name",
    "vram_gb",
    "workload",
    "rank",
    "model_id",
    "model_name",
    "variant",
    "quantization",
    "runtime",
    "estimated_memory_gb",
    "context_tokens",
    "context_target_tokens",
    "tokens_per_second",
    "quality_score",
    "jgb_level",
    "jgb_confidence",
    "fit_score",
    "confidence",
    "reason",
]


def diagnose(rows, hardware, ram, vram, context):
    """Explica por qué un perfil extremo podría producir cero recomendaciones.

    Esta función solo se utiliza como diagnóstico de fallo. No modifica datos.
    Contabiliza las razones de exclusión para que un humano pueda investigar el
    problema sin tener que leer miles de filas a mano.
    """
    limit = ram + vram
    counts = {
        k: 0
        for k in (
            "not_profile",
            "memory",
            "context",
            "runtime",
            "quantization_or_weights",
            "hardware",
            "workload",
            "fits",
        )
    }
    t23 = 0

    for r in rows:
        if (r.get("technical_profile_level") or "") not in ("T2", "T3"):
            counts["not_profile"] += 1
            continue
        t23 += 1

        if r.get("workload") and r["workload"] != "chat":
            counts["workload"] += 1
            continue

        rh = (r.get("hardware_id") or "").strip().lower()
        req = hardware.lower()
        if rh and rh not in req and rh != req:
            counts["hardware"] += 1
            continue

        try:
            mem = float(r.get("estimated_memory_gb") or r.get("weight_memory_gb") or "")
        except ValueError:
            mem = None
        try:
            ctx = float(r.get("context_tokens") or "")
        except ValueError:
            ctx = None

        if mem is None or mem > limit:
            counts["memory"] += 1
            continue
        if ctx is None:
            counts["context"] += 1
            continue
        if not (r.get("runtime") or "").strip():
            counts["runtime"] += 1
            continue
        if not (
            (r.get("quantization") or "").strip()
            or (r.get("weight_memory_gb") or "").strip()
        ):
            counts["quantization_or_weights"] += 1
            continue
        counts["fits"] += 1

    print(
        f"Diagnostic {hardware}: T2/T3={t23}; exclusions="
        + ", ".join(f"{k}={v}" for k, v in counts.items() if v)
    )
    return counts


def run():
    """Genera todas las combinaciones de hardware y escribe la matriz.

    Para cada perfil llamamos al mismo recomendador que utiliza el resto del
    sistema. Esto evita tener dos lógicas distintas de compatibilidad.
    """
    with GPU_FILE.open(encoding="utf-8") as f:
        gpus = list(csv.DictReader(f))

    rows = []
    with FEED.open(encoding="utf-8-sig", newline="") as f:
        feed_rows = list(csv.DictReader(f))

    # El directorio temporal evita que cada ejecución intermedia contamine el
    # CSV definitivo. Solo publicamos la matriz cuando hemos terminado.
    with tempfile.TemporaryDirectory() as td:
        for cpu, cpu_name in CPUS:
            for ram in RAMS:
                # El objetivo de contexto es una política del perfil. No afirma
                # que el modelo soporte ese contexto: luego se limita por lo que
                # el propio modelo demuestra.
                target_context = (
                    2048
                    if ram <= 4
                    else 4096
                    if ram <= 16
                    else 8192
                    if ram <= 64
                    else 16384
                )

                # El primer perfil siempre representa CPU-only. Después se
                # añaden todas las GPU NVIDIA conocidas por el catálogo.
                targets = [("", "Sin GPU", 0)] + [
                    (g["gpu_id"], g["model"], float(g["vram_gb"])) for g in gpus
                ]

                for gid, gname, vram in targets:
                    hardware = f"cpu-{cpu}-{ram}gb" + (f"-{gid}" if gid else "")
                    out = Path(td) / "r.csv"

                    # Reutilizamos el recomendador oficial en lugar de duplicar
                    # aquí sus reglas de memoria, runtime y evidencia.
                    cmd = [
                        "python3",
                        str(RECOMMENDER),
                        "--workload",
                        "chat",
                        "--hardware",
                        hardware,
                        "--ram",
                        str(ram),
                        "--vram",
                        str(vram),
                        "--context",
                        "1",
                        "--out",
                        str(out),
                    ]
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
                    if not out.exists():
                        continue

                    with out.open(encoding="utf-8") as generated:
                        for r in csv.DictReader(generated):
                            try:
                                supported = float(r.get("context_tokens") or "")
                            except (TypeError, ValueError):
                                supported = None

                            # Nunca inventamos contexto. Si el modelo demuestra
                            # 8K y el perfil pide 16K, recomendamos como máximo 8K.
                            recommended = (
                                min(supported, target_context)
                                if supported is not None
                                else ""
                            )
                            r["context_target_tokens"] = recommended

                            rows.append(
                                {
                                    "cpu_family": cpu,
                                    "cpu_name": cpu_name,
                                    "ram_gb": ram,
                                    "gpu_id": gid or "cpu-only",
                                    "gpu_name": gname,
                                    "vram_gb": int(vram),
                                    "workload": "chat",
                                    **{
                                        k: r.get(k, "")
                                        for k in FIELDS
                                        if k
                                        not in {
                                            "cpu_family",
                                            "cpu_name",
                                            "ram_gb",
                                            "gpu_id",
                                            "gpu_name",
                                            "vram_gb",
                                            "workload",
                                        }
                                    },
                                }
                            )

    # Publicamos de una vez la matriz completa.
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)

    print(f"Matrix: {len(rows)} recommendation rows -> {OUT}")

    # Una matriz vacía significa que el pipeline no ha producido una salida útil.
    # En vez de publicar silenciosamente un archivo vacío, generamos diagnóstico
    # y hacemos fallar el workflow para que el problema sea visible.
    if not rows:
        diagnose(feed_rows, "cpu-intel-i5-128gb", 128, 0, 16384)
        if gpus:
            gid = gpus[0]["gpu_id"]
            v = float(gpus[0]["vram_gb"])
            diagnose(feed_rows, f"cpu-intel-i5-128gb-{gid}", 128, v, 16384)
        raise SystemExit("ERROR: la matriz hardware no puede publicarse vacía")


if __name__ == "__main__":
    run()
