#!/usr/bin/env python3
"""Select the highest-AA open model eligible for a supplied hardware profile.

This is the deterministic bridge for the master matrix. The static snapshot
uses the matrix's reference fit approximation; production integration should
replace ``reference_fit`` with the exact LLMFit result and preserve the same
selection contract.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "data" / "master_hardware_model_matrix.v1.json"


def reference_fit(model: dict, ram_gb: int, vram_gb: int) -> tuple[bool, str]:
    p = float(model["params_b"])
    vram_need = p * 0.5 * 1.1
    ram_need = p * 0.5 * 1.2
    if vram_need <= vram_gb:
        return True, "gpu"
    if ram_need <= ram_gb:
        return True, "cpu_or_offload"
    return False, "too_tight"


def recommend(matrix: dict, cpu_tier: str, ram_gb: int, gpu: str) -> dict:
    gpu_rows = [g for g in matrix["gpu_inventory"] if g["model"].lower() == gpu.lower()]
    if not gpu_rows:
        raise ValueError(f"Unknown GPU: {gpu}")
    gpu_row = gpu_rows[0]
    eligible = []
    for model in matrix["model_catalog"]:
        ok, route = reference_fit(model, ram_gb, gpu_row["vram_gb"])
        if ok:
            eligible.append((float(model["aa_score"]), model, route))
    if not eligible:
        return {
            "schema": "leones-recommendation.v1",
            "status": "no_eligible_model",
            "cpu_tier": cpu_tier,
            "ram_gb": ram_gb,
            "gpu": gpu_row,
            "selection": None,
        }
    score, model, route = max(eligible, key=lambda x: x[0])
    return {
        "schema": "leones-recommendation.v1",
        "status": "selected",
        "selection_method": "LLMFit-compatible eligibility reference -> max Artificial Analysis Intelligence Index",
        "fit_authority": "LLMFit",
        "intelligence_authority": matrix["aa_index"],
        "cpu_tier": cpu_tier,
        "ram_gb": ram_gb,
        "gpu": gpu_row,
        "selection": {
            "model_id": model["id"],
            "model_name": model["name"],
            "aa_score": model["aa_score"],
            "aa_score_status": model["aa_score_status"],
            "reference_route": route,
            "physical_benchmark_status": "pending",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-tier", required=True, choices=["i5_ryzen5", "i7_ryzen7", "i9_ryzen9"])
    parser.add_argument("--ram", type=int, required=True, choices=[2, 4, 8, 16, 32, 64])
    parser.add_argument("--gpu", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    result = recommend(matrix, args.cpu_tier, args.ram, args.gpu)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
