#!/usr/bin/env python3
"""Generate reviewable recommendation hypotheses from empirical evidence.

A benchmark score, human preference signal, inference-performance observation,
and local-user measurement are deliberately different evidence classes. This
module never collapses them into a single model score.
"""

from __future__ import annotations
import csv, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data/prospection/atlas_external_evidence.csv"
OUT = ROOT / "data/prospection/atlas_hypotheses.csv"
TOKEN_RE = re.compile(r"(\d+(?:\.\d+)?)\s*tok/s", re.I)
BENCHMARKS = {
    "bigcodebench": "coding",
    "swe-bench": "coding_agentic",
    "livecodebench": "coding_reasoning",
    "gpqa": "reasoning_science",
    "mmlu-pro": "reasoning_general",
    "mmlu": "general_knowledge",
}
ARENA_METRICS = {"elo", "rating", "rank", "win_rate"}
PERFORMANCE_METRICS = {"throughput", "ttft", "latency", "cost_per_1m_tokens"}
FIELDS = [
    "hypothesis_id",
    "model_id",
    "model_name",
    "source_type",
    "source_url",
    "source_record_id",
    "evidence_status",
    "evidence_kind",
    "benchmark",
    "metric",
    "value",
    "unit",
    "hardware_target",
    "quantization",
    "runtime",
    "workload",
    "hypothesis",
    "confidence",
    "next_action",
]


def classify(r: dict, claim: str) -> tuple[str, str, str]:
    source = (r.get("source_type") or "").lower()
    metric = (r.get("metric") or "").lower()
    low = claim.lower()
    benchmark = next(
        (b for b in BENCHMARKS if b in low or b in (r.get("benchmark") or "").lower()),
        "",
    )
    if source in {"lm_arena", "lm arena"} or metric in ARENA_METRICS:
        return (
            "human_preference",
            benchmark,
            "Human preference evidence can prioritize conversational usefulness; it does not establish benchmark capability or local speed.",
        )
    if metric in PERFORMANCE_METRICS or "tok/s" in low or "ttft" in low:
        if source == "msa":
            return (
                "local_performance_observed",
                benchmark,
                "Observed local performance is a strong candidate for reproduction under matched hardware/runtime conditions; do not generalize beyond them.",
            )
        return (
            "inference_performance",
            benchmark,
            "Inference-performance evidence can inform latency/throughput hypotheses, but must not be treated as local-user performance.",
        )
    if benchmark:
        return (
            "benchmark_capability",
            benchmark,
            f"Benchmark evidence supports a {BENCHMARKS[benchmark]} capability hypothesis; it does not establish local throughput.",
        )
    if any(
        x in low for x in ["quant", "precision", "4bit", "8bit", "q4", "q5", "q6", "q8"]
    ):
        return (
            "precision_tradeoff",
            benchmark,
            "Precision evidence suggests a quality/resource trade-off; compare at matched context, runtime and hardware.",
        )
    return (
        "other_reported",
        benchmark,
        "Reported evidence may inform a hypothesis but is insufficient by itself for a recommendation.",
    )


def confidence(kind: str, source: str, has_conditions: bool) -> str:
    if kind == "local_performance_observed" and has_conditions:
        return "medium"
    if (
        kind in {"benchmark_capability", "human_preference", "inference_performance"}
        and source
    ):
        return "low"
    return "low"


def main() -> None:
    rows = []
    if SRC.exists():
        with SRC.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
    out = []
    for idx, r in enumerate(rows, 1):
        claim = (r.get("claim") or "").strip()
        if not claim:
            continue
        kind, benchmark, hypothesis = classify(r, claim)
        source = r.get("source_type", "")
        has_conditions = bool(r.get("hardware") and r.get("runtime"))
        action = {
            "benchmark_capability": "Cross-check with an independent benchmark and test the target workload locally.",
            "human_preference": "Use as a ranking signal for conversational preference; verify target workload independently.",
            "inference_performance": "Compare provider/runtime conditions before using it to estimate local performance.",
            "local_performance_observed": "Reproduce on equivalent LEONES hardware, runtime, quantization and context.",
            "precision_tradeoff": "Test matched quantization, context and runtime on the target hardware.",
            "other_reported": "Seek a second independent source or local measurement before recommendation.",
        }[kind]
        out.append(
            {
                "hypothesis_id": f"H-{idx:06d}",
                "model_id": r.get("model_id", ""),
                "model_name": r.get("model_name", ""),
                "source_type": source,
                "source_url": r.get("source_url", "") or r.get("url", ""),
                "source_record_id": r.get("source_record_id", ""),
                "evidence_status": r.get("evidence_status", "reported"),
                "evidence_kind": kind,
                "benchmark": benchmark,
                "metric": r.get("metric", ""),
                "value": r.get("value", ""),
                "unit": r.get("unit", ""),
                "hardware_target": r.get("hardware", ""),
                "quantization": r.get("quantization", ""),
                "runtime": r.get("runtime", ""),
                "workload": r.get("workload", "") or (BENCHMARKS.get(benchmark, "")),
                "hypothesis": hypothesis,
                "confidence": confidence(kind, source, has_conditions),
                "next_action": action,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)
    print(f"Structured hypotheses: {len(out)} -> {OUT}")


if __name__ == "__main__":
    main()
