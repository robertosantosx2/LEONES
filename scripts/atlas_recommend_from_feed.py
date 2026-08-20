#!/usr/bin/env python3
"""Compatibility CLI for the legacy Atlas recommendation feed.

The canonical model-selection policy lives in :mod:`scripts.model_selector`.
This command intentionally contains no independent scoring or eligibility
logic. It converts the canonical selection result to the historical CSV shape
so existing consumers can migrate without duplicating selection policy.

Economic data is deliberately not used by model selection or fit_score.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from scripts.model_selector import DEFAULT_FEED, select

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/prospection/atlas_recommendations.csv"

FIELDS = [
    "rank", "model_id", "model_name", "variant", "quantization", "runtime",
    "hardware_id", "workload", "estimated_memory_gb", "weight_memory_gb",
    "context_tokens", "context_target_tokens", "tokens_per_second",
    "performance_class", "quality_score", "jgb_level", "jgb_confidence",
    "fit_score", "confidence", "reason", "selection_status",
]


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def _performance_class(value: str | None) -> str:
    try:
        tps = float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        tps = None
    if tps is None:
        return "UNKNOWN"
    if tps < 1:
        return "RULA"
    if tps < 5:
        return "LENTA"
    if tps < 10:
        return "ACEPTABLE"
    if tps < 20:
        return "CABE"
    return "RAPIDA"


def recommend(rows: list[dict[str, str]], *, workload: str, hardware: str,
              ram: float, vram: float, context: int, top_n: int,
              llmfit: dict | None = None, require_llmfit_fit: bool = False) -> dict:
    """Delegate completely to the canonical selector."""
    return select(rows, workload=workload, hardware=hardware, ram_gb=ram,
                  vram_gb=vram, context_tokens=context, top_n=top_n,
                  llmfit=llmfit, require_llmfit_fit=require_llmfit_fit)


def write_legacy_csv(result: dict, source_rows: list[dict[str, str]], output: Path) -> None:
    by_id = {r.get("model_id") or r.get("model_name"): r for r in source_rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        for item in result["candidates"]:
            source = by_id.get(item["model_id"], {})
            evidence = item.get("llmfit") or {}
            row = {field: source.get(field, "") for field in FIELDS}
            row.update({
                "rank": item.get("rank", ""),
                "model_id": item.get("model_id", ""),
                "model_name": item.get("model_name", ""),
                "variant": item.get("variant", ""),
                "quantization": item.get("quantization", ""),
                "runtime": item.get("runtime", ""),
                "context_target_tokens": "",
                "performance_class": _performance_class(source.get("tokens_per_second")),
                "fit_score": item.get("fit_score", ""),
                "confidence": item.get("confidence", ""),
                "reason": "; ".join(item.get("reasons", [])),
                "selection_status": item.get("selection_status", ""),
            })
            if evidence.get("estimated_tps") is not None:
                row["reason"] += f"; LLMFit estimated_tps={evidence['estimated_tps']}"
            writer.writerow(row)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--ram", type=float, required=True)
    parser.add_argument("--vram", type=float, default=0)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path)
    parser.add_argument("--require-llmfit-fit", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    import json
    rows = _load_csv(args.feed)
    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    result = recommend(rows, workload=args.workload, hardware=args.hardware,
                       ram=args.ram, vram=args.vram, context=args.context,
                       top_n=args.top_n, llmfit=llmfit,
                       require_llmfit_fit=args.require_llmfit_fit)
    write_legacy_csv(result, rows, args.out)
    print(f"eligible={result['counts']['eligible']} top_n={result['counts']['top_n']} "
          f"rejected={result['counts']['rejected']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
