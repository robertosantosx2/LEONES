#!/usr/bin/env python3
"""Select model candidates after runtime and hardware are known.

Order is deliberate: workload -> hardware -> runtime -> optimization ->
model eligibility -> ranking. External estimators are evidence, not authority.

The script only reads the feed and writes the requested JSON result. It does
not download models, run inference, or publish anything.
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
DEFAULT_OUT = ROOT / "data/prospection/model_selection.json"
SELECTION_STATES = {"REJECTED", "INELIGIBLE", "CANDIDATE", "SELECTED", "TOP_N", "BENCHMARK_REQUIRED"}


def _num(value: Any) -> float | None:
    """Convert a value to a number, or return None when it is invalid."""
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    """Convert common text and numeric boolean values."""
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return None


def _norm(value: Any) -> str:
    """Normalize text for tolerant comparisons."""
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _params_m(row: dict[str, Any], active: bool = False) -> float | None:
    """Read parameter counts and return them consistently in millions."""
    keys = (
        ["active_parameters_m", "active_params_m", "active_parameters_b", "active_params_b", "active_parameter_count_b", "parameters_active_b", "active_parameters"]
        if active
        else ["total_parameters_m", "parameters_m", "total_params_m", "total_parameters_b", "parameters_total_b", "parameter_count_b", "parameters_b", "total_params_b", "total_parameters", "parameters"]
    )
    for key in keys:
        value = _num(row.get(key))
        if value is None:
            continue
        if key.endswith("_b"):
            return value * 1000.0
        if key.endswith("_m"):
            return value
        if key in {"active_parameters", "active_params", "total_parameters", "parameters"}:
            return value * 1000.0 if value < 1_000_000 else value / 1_000_000.0
        if value >= 1_000_000:
            return value / 1_000_000.0
    return None


def hardware_compatible(declared: str | None, requested: str) -> bool:
    """Check whether a declared hardware profile can serve the request."""
    left = _norm(declared)
    right = _norm(requested)
    return not left or left == right or left in right


def _llmfit_index(payload: Any) -> dict[str, dict[str, Any]]:
    """Index LLMFit candidates by model identity."""
    candidates = payload.get("candidates", []) if isinstance(payload, dict) else payload
    if not isinstance(candidates, list):
        return {}
    index: dict[str, dict[str, Any]] = {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        identity = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        if identity:
            index[_norm(identity)] = item
    return index


def _llmfit_match(row: dict[str, Any], index: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    """Find the LLMFit record matching a model row."""
    for key in (row.get("model_id"), row.get("model_name"), row.get("name")):
        if key and _norm(key) in index:
            return index[_norm(key)]
    return None


def _runtime_evidence(row: dict[str, Any]) -> dict[str, Any]:
    """Build the runtime-relevant evidence block used in the result."""
    total_m = _params_m(row, False)
    active_m = _params_m(row, True)
    is_moe = _bool(row.get("is_moe"))
    agentic = _bool(row.get("agentic"))
    basis = "active_parameters_m" if is_moe else "total_parameters_m"
    return {
        "model": {
            "total_params_m": total_m,
            "active_params_m": active_m,
            "total_params_b": total_m / 1000 if total_m is not None else None,
            "active_params_b": active_m / 1000 if active_m is not None else None,
            "quantized_weight_gb": _num(row.get("quantized_weight_gb") or row.get("weight_memory_gb")),
        },
        "moe": {"is_moe": is_moe} if is_moe is not None else {},
        "workload": {"agentic": agentic} if agentic is not None else {},
        "parameter_selection_basis": basis,
    }


def eligibility(row: dict[str, Any], *, workload: str, hardware: str, ram_gb: float, vram_gb: float = 0, context_tokens: int = 4096, llmfit: dict[str, Any] | None = None, require_llmfit_fit: bool = False, required_runtime: str | None = None, optimization_families: list[str] | None = None) -> tuple[bool, list[str], dict[str, Any]]:
    """Apply eligibility gates and return reasons plus evidence."""
    evidence: dict[str, Any] = {}
    model_id = row.get("model_id") or row.get("model_name")
    if not model_id:
        return False, ["missing model identity"], evidence
    if not workload.strip():
        return False, ["use case/workload is required"], evidence
    if not hardware.strip():
        return False, ["hardware profile is required"], evidence
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
    if not runtime:
        return False, ["runtime is unknown"], evidence
    if required_runtime and _norm(runtime) != _norm(required_runtime):
        return False, [f"runtime mismatch: {runtime!r} != {required_runtime!r}"], evidence
    evidence["runtime"] = runtime
    evidence["quantization"] = quant or "observed-weight"
    declared_opts = [item.strip() for item in str(row.get("optimization_families") or "").split(",") if item.strip()]
    required_opts = optimization_families or []
    if required_opts and not declared_opts:
        return False, ["candidate has no declared optimization compatibility"], evidence
    declared_normalized = {_norm(item) for item in declared_opts}
    missing_opts = [item for item in required_opts if _norm(item) not in declared_normalized]
    if missing_opts:
        return False, [f"candidate lacks selected optimization families: {missing_opts}"], evidence
    evidence["optimization_families"] = required_opts
    observed_weight = _num(row.get("weight_memory_gb"))
    memory = _num(row.get("estimated_memory_gb")) or observed_weight
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
    return True, ["passes use-case, hardware, runtime and optimization gates"], evidence


def score(row: dict[str, Any], evidence: dict[str, Any]) -> tuple[float, list[str]]:
    """Calculate the transparent ranking score and its reasons."""
    quality = _num(row.get("quality_score"))
    tps = _num(row.get("tokens_per_second"))
    memory = evidence.get("memory_required_gb")
    available = max(evidence.get("memory_available_gb") or 1, 1)
    jgb = _num(row.get("jgb_level"))
    quality_score = quality / 100 if quality is not None else 0.0
    performance_score = min(max(tps or 0, 0) / 50, 1.0)
    headroom = max(0.0, 1.0 - (memory or available) / available)
    openness = min(max(jgb or 0, 0) / 5, 1.0)
    llmfit = evidence.get("llmfit") or {}
    estimate = min(max(_num(llmfit.get("estimated_tps")) or 0, 0) / 50, 1.0)
    value = 0.35 * quality_score + 0.25 * performance_score + 0.15 * headroom + 0.15 * estimate + 0.10 * openness
    reasons = [
        f"quality={quality if quality is not None else 'unknown'}",
        f"measured_tps={tps if tps is not None else 'unknown'}",
        f"llmfit_estimated_tps={llmfit.get('estimated_tps', 'unknown')}",
        f"memory_headroom={headroom:.3f}",
        f"JGB={int(jgb) if jgb is not None else 'unknown'}",
    ]
    return round(value, 6), reasons


def select(rows: Iterable[dict[str, Any]], *, workload: str, hardware: str, ram_gb: float, vram_gb: float = 0, context_tokens: int = 4096, top_n: int = 10, llmfit: dict[str, Any] | None = None, require_llmfit_fit: bool = False, required_runtime: str | None = None, optimization_families: list[str] | None = None) -> dict[str, Any]:
    """Select, rank and explain eligible models."""
    if not required_runtime:
        raise ValueError("inference runtime must be decided before model evaluation")
    rows = list(rows)
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in rows:
        ok, reasons, evidence = eligibility(row, workload=workload, hardware=hardware, ram_gb=ram_gb, vram_gb=vram_gb, context_tokens=context_tokens, llmfit=llmfit, require_llmfit_fit=require_llmfit_fit, required_runtime=required_runtime, optimization_families=optimization_families)
        model_id = row.get("model_id") or row.get("model_name")
        if not ok:
            rejected.append({"model_id": model_id, "selection_status": "REJECTED", "reasons": reasons})
            continue
        fit_score, score_reasons = score(row, evidence)
        runtime_evidence = _runtime_evidence(row)
        is_moe = runtime_evidence["moe"].get("is_moe") is True
        category = row.get("category") or row.get("modality") or row.get("type")
        selected.append({
            "model_id": model_id,
            "model_name": row.get("model_name") or model_id,
            "category": category,
            "architecture_class": "moe" if is_moe else "dense",
            "total_parameters_m": runtime_evidence["model"]["total_params_m"],
            "active_parameters_m": runtime_evidence["model"]["active_params_m"],
            "parameter_selection_basis": runtime_evidence["parameter_selection_basis"],
            "variant": row.get("variant"),
            "quantization": row.get("quantization"),
            "runtime": row.get("runtime"),
            "optimization_families": optimization_families or [],
            "selection_status": "CANDIDATE",
            "task_fit": "compatible",
            "hardware_fit": "compatible",
            "memory_fit": "compatible",
            "context_fit": "supported" if evidence.get("context_supported") is not None else "unknown",
            "runtime_fit": "preselected",
            "evidence_level": evidence.get("evidence_level"),
            "llmfit": evidence.get("llmfit"),
            "fit_score": fit_score,
            "confidence": "high" if row.get("quality_score") and row.get("tokens_per_second") else "medium",
            "model": runtime_evidence["model"],
            "moe": runtime_evidence["moe"],
            "workload": runtime_evidence["workload"],
            "reasons": reasons + score_reasons,
        })
    selected.sort(key=lambda item: (-item["fit_score"], _norm(item["model_id"])))
    for index, item in enumerate(selected):
        item["rank"] = index + 1
        item["selection_status"] = "TOP_N" if index < max(0, top_n) else "SELECTED"
    top = selected[: max(0, top_n)]
    for item in top:
        if not item.get("llmfit") or not item["llmfit"].get("estimated_tps"):
            item["selection_status"] = "BENCHMARK_REQUIRED"
    return {
        "schema_version": "1.0",
        "selector": "LEONES-model-selection",
        "inference_configuration": {"workload": workload, "runtime": required_runtime, "optimization_families": optimization_families or [], "measurement": "not_measured"},
        "selection_policy": {"workload": workload, "hardware": hardware, "ram_gb": ram_gb, "vram_gb": vram_gb, "context_tokens": context_tokens, "top_n": top_n, "price_in_score": False, "measured_performance_required_for_final_claim": True},
        "counts": {"input": len(rows), "eligible": len(selected), "rejected": len(rejected), "top_n": len(top)},
        "candidates": selected,
        "rejected": rejected,
    }


def _load_csv(path: Path) -> list[dict[str, str]]:
    """Load the model feed as dictionaries."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    """Parse the CLI, select candidates and write the JSON result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workload", required=True)
    parser.add_argument("--hardware", required=True)
    parser.add_argument("--ram", type=float, required=True)
    parser.add_argument("--vram", type=float, default=0)
    parser.add_argument("--runtime", required=True)
    parser.add_argument("--optimization", action="append", default=[])
    parser.add_argument("--context", type=int, default=4096)
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--feed", type=Path, default=DEFAULT_FEED)
    parser.add_argument("--llmfit", type=Path)
    parser.add_argument("--require-llmfit-fit", action="store_true")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    rows = _load_csv(args.feed)
    llmfit = json.loads(args.llmfit.read_text(encoding="utf-8")) if args.llmfit else None
    result = select(rows, workload=args.workload, hardware=args.hardware, ram_gb=args.ram, vram_gb=args.vram, context_tokens=args.context, top_n=args.top_n, llmfit=llmfit, require_llmfit_fit=args.require_llmfit_fit, required_runtime=args.runtime, optimization_families=args.optimization)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"selected={result['counts']['eligible']} top_n={result['counts']['top_n']} rejected={result['counts']['rejected']} -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
