#!/usr/bin/env python3
"""Canonical LEONES model-selection layer.

Selection is deliberately split from ranking and measurement:

1. eligibility removes models that cannot be justified for the requested task
   and hardware;
2. LLMFit is an optional pre-filter/estimate and is never a measurement;
3. ranking orders the eligible candidates without using hardware price;
4. the output explains every rejection and every selected candidate.

The module is dependency-free and can be used by H10, the web application and
future routers. It consumes Atlas/feed-style dictionaries rather than owning a
second model catalogue.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FEED = ROOT / "data/prospection/atlas_feed.csv"
DEFAULT_LLMFIT = ROOT / "data/prospection/llmfit_candidates.json"
DEFAULT_OUT = ROOT / "data/prospection/model_selection.json"

SELECTION_STATES = {"REJECTED", "INELIGIBLE", "CANDIDATE", "SELECTED", "TOP_N", "BENCHMARK_REQUIRED"}


def _num(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _boolish(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "ok"}


def hardware_compatible(declared: str | None, requested: str) -> bool:
    """Return true when the feed has no restriction or matches the profile."""
    left, right = _norm(declared), _norm(requested)
    return not left or left == right or left in right


def _llmfit_index(payload: Any) -> dict[str, dict[str, Any]]:
    """Index normalized or raw LLMFit candidates by model id/name."""
    if not payload:
        return {}
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else payload
    index: dict[str, dict[str, Any]] = {}
    for item in candidates if isinstance(candidates, list) else []:
        if not isinstance(item, dict):
            continue
        model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        if model_id:
            index[_norm(model_id)] = item
    return index


def _llmfit_match(row: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    for key in (row.get("model_id"), row.get("model_name"), row.get("name")):
        if key and _norm(key) in index:
            return index[_norm(key)]
    return None


def eligibility(row: dict[str, Any], *, workload: str, hardware: str, ram_gb: float,
                vram_gb: float = 0, context_tokens: int = 4096,
                llmfit: dict[str, Any] | None = None,
                require_llmfit_fit: bool = False) -> tuple[bool, list[str], dict[str, Any]]:
    """Apply hard selection rules and return (eligible, reasons, evidence)."""
    reasons: list[str] = []
    evidence: dict[str, Any] = {}
    model_id = row.get("model_id") or row.get("model_name")
    if not model_id:
        return False, ["missing model identity"], evidence

    row_workload = (row.get("workload") or "").strip()
    if row_workload and row_workload != workload:
        return False, [f"workload mismatch: {row_workload!r} != {workload!r}"], evidence

    if not hardware_compatible(row.get("hardware_id"), hardware):
        return False, ["declared hardware profile is incompatible"], evidence

    level = (row.get("technical_profile_level") or "").strip()
    if level not in {"T2", "T3"}:
        return False, [f"technical evidence level {level or 'unknown'} is below T2"], evidence
    evidence["evidence_level"] = level

    runtime = (row.get("runtime") or "").strip()
    quant = (row.get("quantization") or "").strip()
    observed_weight = _num(row.get("weight_memory_gb"))
    if not runtime:
        return False, ["runtime is unknown"], evidence
    if not quant and observed_weight is None:
        return False, ["quantization or observed weight size is unknown"], evidence
    evidence["runtime"] = runtime
    evidence["quantization"] = quant or "observed-weight"

    memory = _num(row.get("estimated_memory_gb"))
    if memory is None:
        memory = observed_weight
    if memory is None:
        return False, ["memory requirement is unknown"], evidence
    available = max(0.0, ram_gb + vram_gb)
    evidence["memory_required_gb"] = memory
    evidence["memory_available_gb"] = available
    if memory > available:
        return False, [f"memory requirement {memory:g} GB exceeds available {available:g} GB"], evidence

    supported_context = _num(row.get("context_tokens"))
    if supported_context is not None and supported_context < 1:
        return False, ["invalid supported context"], evidence
    evidence["context_supported"] = int(supported_context) if supported_context is not None else None
    evidence["context_target"] = context_tokens
    evidence["context_recommended"] = min(int(supported_context), context_tokens) if supported_context is not None else None

    match = _llmfit_match(row, _llmfit_index(llmfit)) if llmfit else None
    if match:
        fit = match.get("fit_level") or match.get("fit")
        estimated_tps = _num(match.get("estimated_tps") or match.get("tok_s") or match.get("tps"))
        evidence["llmfit"] = {
            "fit_level": fit,
            "estimated_tps": estimated_tps,
            "memory_required_gb": _num(match.get("memory_required_gb") or match.get("memory_gb")),
            "basis": "llmfit-estimate",
        }
        if require_llmfit_fit and not fit:
            return False, ["LLMFit result has no fit classification"], evidence
        if str(fit).lower() in {"no", "impossible", "cannot", "does not fit"}:
            return False, [f"LLMFit rejects candidate: {fit}"], evidence
    else:
        evidence["llmfit"] = None
        if require_llmfit_fit:
            return False, ["no LLMFit candidate available"], evidence

    return True, ["passes hard technical selection rules"], evidence


def score(row: dict[str, Any], evidence: dict[str, Any], *, prefer_open: bool = False) -> tuple[float, list[str]]:
    """Score an eligible candidate. Price is intentionally excluded."""
    quality = _num(row.get("quality_score"))
    tps = _num(row.get("tokens_per_second"))
    memory = evidence.get("memory_required_gb")
    available = max(evidence.get("memory_available_gb") or 1, 1)
    jgb = _num(row.get("jgb_level"))

    q = (quality / 100) if quality is not None else 0.0
    p = min(max(tps or 0, 0) / 50, 1.0)
    headroom = max(0.0, 1.0 - (memory or available) / available)
    openness = min(max(jgb or 0, 0) / 5, 1.0)
    llmfit = evidence.get("llmfit") or {}
    estimate = min(max(_num(llmfit.get("estimated_tps")) or 0, 0) / 50, 1.0)

    # Missing evidence contributes zero; it is never fabricated.
    value = 0.35 * q + 0.25 * p + 0.15 * headroom + 0.15 * estimate
    if prefer_open:
        value += 0.10 * openness
    else:
        value += 0.10 * openness

    reasons = [
        f"quality={quality if quality is not None else 'unknown'}",
        f"measured_tps={tps if tps is not None else 'unknown'}",
        f"llmfit_estimated_tps={llmfit.get('estimated_tps', 'unknown')}",
        f"memory_headroom={headroom:.3f}",
        f"JGB={int(jgb) if jgb is not None else 'unknown'}",
    ]
    return round(value, 6), reasons


def select(rows: Iterable[dict[str, Any]], *, workload: str, hardware: str, ram_gb: float,
           vram_gb: float = 0, context_tokens: int = 4096, top_n: int = 10,
           llmfit: dict[str, Any] | None = None,
           require_llmfit_fit: bool = False,
           prefer_open: bool = False) -> dict[str, Any]:
    """Produce the canonical, deterministic selection result."""
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        ok, reasons, evidence = eligibility(
            row, workload=workload, hardware=hardware, ram_gb=ram_gb,
            vram_gb=vram_gb, context_tokens=context_tokens,
            llmfit=llmfit, require_llmfit_fit=require_llmfit_fit,
        )
        if not ok:
            rejected.append({"model_id": row.get("model_id") or row.get("model_name"), "selection_status": "REJECTED", "reasons": reasons})
            continue
        fit_score, score_reasons = score(row, evidence, prefer_open=prefer_open)
        selected.append({
            "model_id": row.get("model_id") or row.get("model_name"),
            "model_name": row.get("model_name") or row.get("model_id"),
            "variant": row.get("variant"),
            "quantization": row.get("quantization"),
            "runtime": row.get("runtime"),
            "selection_status": "CANDIDATE",
            "task_fit": "compatible",
            "hardware_fit": "compatible",
            "memory_fit": "compatible",
            "context_fit": "supported" if evidence.get("context_supported") is not None else "unknown",
            "runtime_fit": "declared",
            "evidence_level": evidence.get("evidence_level"),
            "llmfit": evidence.get("llmfit"),
            "fit_score": fit_score,
            "confidence": "high" if row.get("quality_score") and row.get("tokens_per_second") else "medium",
            "reasons": reasons + score_reasons,
        })

    selected.sort(key=lambda x: (-x["fit_score"], _norm(x["model_id"])))
    for index, item in enumerate(selected):
        item["rank"] = index + 1
        if index < max(0, top_n):
            item["selection_status"] = "TOP_N"
        else:
            item["selection_status"] = "SELECTED"
    top = selected[:max(0, top_n)]
    for item in top:
        if not item.get("llmfit") or not item["llmfit"].get("estimated_tps"):
            item["selection_status"] = "BENCHMARK_REQUIRED"

    return {
        "schema_version": "1.0",
        "selector": "LEONES-model-selection",
        "selection_policy": {
            "workload": workload,
            "hardware": hardware,
            "ram_gb": ram_gb,
            "vram_gb": vram_gb,
            "context_tokens": context_tokens,
            "top_n": top_n,
            "price_in_score": False,
            "measured_performance_required_for_final_claim": True,
        },
        "counts": {"input": len(list(rows)) if not isinstance(rows, list) else len(rows), "eligible": len(selected), "rejected": len(rejected), "top_n": len(top)},
        "candidates": selected,
        "rejected": rejected,
    }


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


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
    parser.add_argument("--prefer-open", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    rows = _load_csv(args.feed)
    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    result = select(rows, workload=args.workload, hardware=args.hardware, ram_gb=args.ram,
                    vram_gb=args.vram, context_tokens=args.context, top_n=args.top_n,
                    llmfit=llmfit, require_llmfit_fit=args.require_llmfit_fit,
                    prefer_open=args.prefer_open)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"selected={result['counts']['eligible']} top_n={result['counts']['top_n']} rejected={result['counts']['rejected']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
