#!/usr/bin/env python3
"""Generate structured recommendation hypotheses from empirical evidence.

Hypotheses are reviewable candidates, never verified recommendations. The
script preserves the distinction between benchmark quality, local throughput,
hardware constraints and evidence provenance.
"""
from __future__ import annotations
import csv, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data/prospection/atlas_external_evidence.csv"
OUT = ROOT / "data/prospection/atlas_hypotheses.csv"

TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*tok/s", re.I)
GPU_RE = re.compile(r"(\d+(?:\.\d+)?)\s*GB\s*(?:card|GPU|VRAM)", re.I)
QUANT_RE = re.compile(r"\b(Q[2-8](?:_[A-Z0-9_]+)?)\b", re.I)
BENCHMARKS = {
    "bigcodebench": "coding",
    "swe-bench": "coding_agentic",
    "livecodebench": "coding_reasoning",
    "gpqa": "reasoning_science",
    "mmlu": "general_knowledge",
    "mmlu-pro": "reasoning_general",
}

FIELDS = [
    "hypothesis_id", "model_id", "model_name", "source_type", "source_url",
    "source_record_id", "evidence_status", "evidence_kind", "benchmark",
    "metric", "value", "unit", "hardware_target", "quantization",
    "runtime", "workload", "hypothesis", "confidence", "next_action",
]

def confidence(kind: str, detail: int) -> str:
    if kind == "local_performance" and detail >= 3:
        return "medium"
    if kind in {"benchmark_quality", "precision_tradeoff"} and detail >= 2:
        return "medium"
    return "low"

def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    if SRC.exists():
        with SRC.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))

    out = []
    for idx, r in enumerate(rows, 1):
        claim = (r.get("claim") or r.get("text") or "").strip()
        low = claim.lower()
        if not claim:
            continue
        tokens = TOKEN_RE.search(claim)
        gpu = GPU_RE.search(claim)
        quant = QUANT_RE.search(claim)
        benchmark = next((b for b in BENCHMARKS if b in low), "")
        kind = ""
        hypothesis = ""
        next_action = ""
        metric = ""
        value = ""
        unit = ""
        hardware = gpu.group(1) + " GB GPU/VRAM" if gpu else ""
        runtime = ""

        if tokens:
            kind = "local_performance"
            metric = "throughput"
            value = tokens.group(1)
            unit = "tok/s"
            hypothesis = "Candidate for local RULA at the observed hardware/runtime conditions; do not generalize beyond those conditions."
            next_action = "Reproduce on equivalent LEONES hardware, runtime and quantization."
            if "llama-server" in low: runtime = "llama-server"
        elif benchmark:
            kind = "benchmark_quality"
            metric = "benchmark_score"
            hypothesis = f"Candidate {BENCHMARKS[benchmark]} model; benchmark evidence supports capability hypothesis, not local throughput."
            next_action = "Cross-check independent benchmark evidence and test the target workload locally."
        elif "precision" in low or "quant" in low or quant:
            kind = "precision_tradeoff"
            metric = "quantization_observation"
            hypothesis = "Candidate precision/quality trade-off; compare CABE and RULA at the same hardware target."
            next_action = "Test at matched quantization, context and runtime on target hardware."

        if not kind:
            continue
        detail = sum(bool(x) for x in [r.get("source_type"), r.get("url"), claim, r.get("model_id"), quant, gpu, tokens])
        out.append({
            "hypothesis_id": f"H-{idx:06d}",
            "model_id": r.get("model_id", ""),
            "model_name": r.get("model_name", ""),
            "source_type": r.get("source_type", ""),
            "source_url": r.get("url", ""),
            "source_record_id": r.get("source_record_id", ""),
            "evidence_status": r.get("evidence_status", "reported"),
            "evidence_kind": kind,
            "benchmark": benchmark,
            "metric": metric,
            "value": value,
            "unit": unit,
            "hardware_target": hardware,
            "quantization": quant.group(1) if quant else "",
            "runtime": runtime,
            "workload": BENCHMARKS.get(benchmark, "local inference" if tokens else "precision evaluation"),
            "hypothesis": hypothesis,
            "confidence": confidence(kind, detail),
            "next_action": next_action,
        })

    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader(); w.writerows(out)
    print(f"Structured hypotheses: {len(out)} -> {OUT}")

if __name__ == "__main__":
    main()
