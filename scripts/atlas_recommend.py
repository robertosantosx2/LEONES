#!/usr/bin/env python3
"""Generate deterministic Atlas recommendations from the normalized feed."""
from __future__ import annotations

import argparse
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE_PATH = ROOT / "web" / "proyectos" / "atlas" / "recommendation_engine.py"
FEED = ROOT / "data" / "prospection" / "atlas_feed.csv"
OUT = ROOT / "data" / "prospection" / "atlas_recommendations.csv"

spec = importlib.util.spec_from_file_location("atlas_engine", ENGINE_PATH)
engine = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(engine)


def as_float(value: str):
    return float(value) if value not in ("", None) else None


def as_int(value: str):
    return int(value) if value not in ("", None) else None


def load_deployments():
    deployments = []
    with FEED.open("r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            deployments.append(engine.Deployment(
                deployment_id=f"{row.get('model_id','')}|{row.get('variant','')}|{row.get('quantization','')}|{row.get('runtime','')}|{row.get('hardware_id','')}|{row.get('workload','')}",
                model_id=row.get("model_id", ""),
                estimated_memory_gb=as_float(row.get("estimated_memory_gb", "")) or 0.0,
                context_tokens=as_int(row.get("context_tokens", "")) or 0,
                supported_workloads={row["workload"]} if row.get("workload") else set(),
                supported_hardware={row["hardware_id"]} if row.get("hardware_id") else set(),
                supported_runtimes={row["runtime"]} if row.get("runtime") else set(),
                quality_score=as_float(row.get("quality_score", "")),
                tokens_per_second=as_float(row.get("tokens_per_second", "")),
                jgb_level=as_int(row.get("jgb_level", "")),
                jgb_confidence=row.get("jgb_confidence", "unknown") or "unknown",
                notes=row.get("notes", ""),
            ))
    return deployments


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--ram", type=float, required=True)
    parser.add_argument("--vram", type=float, default=0.0)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--min-tps", type=float)
    parser.add_argument("--required-jgb", type=int)
    parser.add_argument("--prefer-jgb", action="store_true")
    args = parser.parse_args()

    request = engine.Request(
        workload=args.workload,
        hardware_name=args.hardware,
        hardware_ram_gb=args.ram,
        hardware_vram_gb=args.vram,
        required_context_tokens=args.context,
        min_tokens_per_second=args.min_tps,
        required_jgb_level=args.required_jgb,
        prefer_jgb=args.prefer_jgb,
    )
    results = engine.recommend(request, load_deployments())

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["rank", "model_id", "deployment_id", "viable", "fit_score", "confidence", "explanation"])
        for r in results:
            writer.writerow([r.rank, r.model_id, r.deployment_id, r.viable, f"{r.fit_score:.4f}", r.confidence, " | ".join(r.explanation)])

    for r in results:
        print(f"{r.rank:>3}  {r.model_id:<24} {r.fit_score:.4f}  {r.confidence:<6}  {'; '.join(r.explanation)}")


if __name__ == "__main__":
    main()
