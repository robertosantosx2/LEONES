#!/usr/bin/env python3
"""Structured adapters for Atlas empirical sources.

This layer deliberately normalizes provenance and claims without asserting
that external observations are verified by LEONES. Each adapter may be
implemented incrementally; unsupported dynamic APIs are recorded rather than
scraped with guessed semantics.
"""

from __future__ import annotations
import csv, datetime as dt, hashlib, pathlib
from dataclasses import dataclass, asdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"


@dataclass
class Evidence:
    model_id: str = ""
    model_name: str = ""
    source_type: str = ""
    source_url: str = ""
    retrieved_at: str = ""
    claim: str = ""
    metric: str = ""
    value: str = ""
    unit: str = ""
    benchmark: str = ""
    hardware: str = ""
    runtime: str = ""
    quantization: str = ""
    workload: str = ""
    evidence_status: str = "reported"
    source_record_id: str = ""
    extraction_method: str = "adapter"


def record(source_type: str, url: str, claim: str, **kw) -> Evidence:
    now = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    key = f"{source_type}|{url}|{claim}".encode()
    rid = hashlib.sha256(key).hexdigest()[:16]
    return Evidence(
        source_type=source_type,
        source_url=url,
        retrieved_at=now,
        claim=claim,
        source_record_id=f"{source_type}:{rid}",
        **kw,
    )


class HuggingFaceAdapter:
    name = "hugging_face"
    url = "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard"

    def normalize(
        self,
        model_name: str,
        benchmark: str,
        metric: str,
        value: str,
        precision: str = "",
    ) -> Evidence:
        return record(
            self.name,
            self.url,
            f"{model_name}: {benchmark} {metric}={value}"
            + (f" ({precision})" if precision else ""),
            model_name=model_name,
            benchmark=benchmark,
            metric=metric,
            value=value,
            unit="score",
            quantization=precision,
        )


class LMSEvalAdapter:
    name = "lm_arena"
    url = "https://chat.lmsys.org/"

    def normalize(
        self, model_name: str, rank_or_rating: str, metric: str = "rating"
    ) -> Evidence:
        return record(
            self.name,
            self.url,
            f"{model_name}: {metric}={rank_or_rating}",
            model_name=model_name,
            metric=metric,
            value=rank_or_rating,
            unit="rating" if metric.lower() != "rank" else "rank",
        )


class ArtificialAnalysisAdapter:
    name = "artificial_analysis"
    url = "https://artificialanalysis.ai/"

    def normalize(
        self,
        model_name: str,
        metric: str,
        value: str,
        unit: str,
        provider_or_hardware: str = "",
    ) -> Evidence:
        return record(
            self.name,
            self.url,
            f"{model_name}: {metric}={value} {unit}",
            model_name=model_name,
            metric=metric,
            value=value,
            unit=unit,
            hardware=provider_or_hardware,
        )


class MSAAdapter:
    name = "msa"
    url = "https://msa.millaguie.net/"

    def normalize(
        self,
        model_name: str,
        claim: str,
        metric: str = "",
        value: str = "",
        unit: str = "",
        hardware: str = "",
        runtime: str = "",
        quantization: str = "",
    ) -> Evidence:
        return record(
            self.name,
            self.url,
            claim,
            model_name=model_name,
            metric=metric,
            value=value,
            unit=unit,
            hardware=hardware,
            runtime=runtime,
            quantization=quantization,
        )


class BenchmarkAdapter:
    def __init__(self, name: str, url: str):
        self.name, self.url = name, url

    def normalize(
        self,
        model_name: str,
        benchmark: str,
        metric: str,
        value: str,
        workload: str = "",
    ) -> Evidence:
        return record(
            self.name,
            self.url,
            f"{model_name}: {benchmark} {metric}={value}",
            model_name=model_name,
            benchmark=benchmark,
            metric=metric,
            value=value,
            unit="score",
            workload=workload,
        )


def write(rows: list[Evidence]) -> None:
    if not rows:
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))
    fields = list(asdict(rows[0]).keys())
    if existing:
        fields = list(dict.fromkeys(fields + list(existing[0].keys())))
    seen = {(r.get("source_type"), r.get("source_record_id")) for r in existing}
    for row in rows:
        d = asdict(row)
        if (d["source_type"], d["source_record_id"]) not in seen:
            existing.append(d)
            seen.add((d["source_type"], d["source_record_id"]))
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)


if __name__ == "__main__":
    # Adapter registry / smoke test. Real extraction is deliberately delegated
    # to source-specific API/dataset clients rather than guessed HTML scraping.
    adapters = [
        HuggingFaceAdapter(),
        LMSEvalAdapter(),
        ArtificialAnalysisAdapter(),
        MSAAdapter(),
        BenchmarkAdapter("swe_bench", "https://www.swebench.com/"),
        BenchmarkAdapter("livecodebench", "https://livecodebench.github.io/"),
        BenchmarkAdapter("llm_stats", "https://llm-stats.com/benchmarks"),
        BenchmarkAdapter("vellum", "https://www.vellum.ai/llm-leaderboard"),
        BenchmarkAdapter("lambda", "https://lambda.ai/llm-benchmarks-leaderboard"),
    ]
    print("Registered empirical adapters:", ", ".join(a.name for a in adapters))
