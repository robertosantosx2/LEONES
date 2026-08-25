#!/usr/bin/env python3
"""Bridge normalized LLMFit discovery into LEONES recommendation candidates.

This is deliberately an adapter, not a second selector. LLMFit remains an
external estimator; the canonical selector decides eligibility/ranking and
marks candidates that still require a real benchmark.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from automation.discovery.llmfit_adapter import normalize
from scripts.model_selector import DEFAULT_FEED, select

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "data/prospection/llmfit_recommendation_candidates.json"


def _load_feed(path: Path) -> list[dict[str, Any]]:
    import csv
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def build_candidates(*, feed: list[dict[str, Any]], llmfit_payload: Any,
                     workload: str, hardware: str, ram_gb: float,
                     vram_gb: float = 0, context_tokens: int = 4096,
                     top_n: int = 10, require_llmfit_fit: bool = False) -> dict[str, Any]:
    """Return canonical selector output plus explicit LLMFit provenance."""
    external = normalize(llmfit_payload)
    result = select(feed, workload=workload, hardware=hardware, ram_gb=ram_gb,
                    vram_gb=vram_gb, context_tokens=context_tokens, top_n=top_n,
                    llmfit=external, require_llmfit_fit=require_llmfit_fit)
    result["llmfit_provenance"] = {
        "source": external["source"],
        "source_version": external.get("source_version"),
        "observed_at": external.get("observed_at"),
        "hardware": external.get("hardware"),
        "estimate_only": True,
        "measured_tps_is_null": all(c.get("measured_tps") is None for c in external["candidates"]),
    }
    for candidate in result["candidates"]:
        candidate["llmfit_provenance"] = {
            "source": "llmfit",
            "estimate_only": True,
            "estimated_tps": (candidate.get("llmfit") or {}).get("estimated_tps"),
            "measured_tps": None,
        }
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llmfit", type=Path, required=True)
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--ram", type=float, required=True)
    parser.add_argument("--vram", type=float, default=0)
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--require-llmfit-fit", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    payload = json.loads(args.llmfit.read_text(encoding="utf-8"))
    result = build_candidates(
        feed=_load_feed(args.feed), llmfit_payload=payload,
        workload=args.workload, hardware=args.hardware, ram_gb=args.ram,
        vram_gb=args.vram, context_tokens=args.context, top_n=args.top_n,
        require_llmfit_fit=args.require_llmfit_fit,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
