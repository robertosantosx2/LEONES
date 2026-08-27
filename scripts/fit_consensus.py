"""Normalize six fit estimators and reduce candidates by category.

Contract: 6 estimators x 6 models x 3 categories = 108 external candidates.
The selector keeps 3 representatives per category: smallest, lower-middle,
and largest. Dense uses total parameters; MoE uses active parameters.
All parameter counts are normalized to millions. External values are not measurements.
"""
from __future__ import annotations
from typing import Any
import re

SOURCES = ("llmfit", "canirun_ai", "localmodel_run", "vrambudget", "llm_checker", "llm_hardware_advisor")
CATEGORIES = ("text", "image", "video")
ESTIMATOR_CANDIDATE_COUNT = 6
SELECTED_REPRESENTATIVE_COUNT = 3
EXPECTED_EXTERNAL_CANDIDATES = len(SOURCES) * len(CATEGORIES) * ESTIMATOR_CANDIDATE_COUNT


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _items(payload: Any) -> list[dict[str, Any]]:
    items = payload.get("candidates", []) if isinstance(payload, dict) else payload
    return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []


def _category(item: dict[str, Any]) -> str | None:
    text = _norm(item.get("category") or item.get("modality") or item.get("type"))
    aliases = {"text":"text","llm":"text","language":"text","image":"image","vision":"image","multimodal image":"image","video":"video","video generation":"video","video model":"video"}
    return aliases.get(text)


def _parse_parameter_value(value: Any) -> tuple[float, str] | None:
    if value in (None, ""): return None
    if isinstance(value, (int, float)):
        return float(value), "raw"
    text = str(value).strip().lower().replace(",", "")
    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)\s*([kmbt])?", text)
    if not match: return None
    number = float(match.group(1)); suffix = match.group(2) or "raw"
    return number, suffix


def _to_millions(parsed: tuple[float, str]) -> float:
    number, suffix = parsed
    if suffix == "b": return number * 1000.0
    if suffix == "m": return number
    if suffix == "k": return number / 1000.0
    if suffix == "t": return number * 1_000_000.0
    return number / 1_000_000.0 if number >= 1_000_000 else number * 1000.0


def _params_m(item: dict[str, Any], active: bool = False) -> float | None:
    if active:
        keys = ["active_parameters_m","active_params_m","active_parameter_count_m","active_parameters_b","active_params_b","active_parameter_count_b","active_parameters","active_params","active_parameter_count"]
    else:
        keys = ["total_parameters_m","parameters_m","parameter_count_m","params_m","total_params_m","total_parameters_b","parameters_b","parameter_count_b","params_b","total_params_b","total_parameters","parameters","parameter_count","params"]
    for key in keys:
        parsed = _parse_parameter_value(item.get(key))
        if parsed is None: continue
        return _to_millions(parsed)
    return None


def _is_moe(item: dict[str, Any]) -> bool:
    value = item.get("is_moe")
    if isinstance(value, bool): return value
    text = _norm(value or item.get("architecture") or item.get("model_type"))
    return text in {"moe","mixture of experts","mixture experts"} or "moe" in text


def normalize_candidate(item: dict[str, Any], estimator: str) -> dict[str, Any] | None:
    model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
    category = _category(item)
    total_m = _params_m(item, False)
    if not model_id or category is None or total_m is None or total_m <= 0: return None
    moe = _is_moe(item)
    active_m = _params_m(item, True) if moe else None
    if moe and (active_m is None or active_m <= 0 or active_m > total_m): return None
    return {**item,"model_id":model_id,"category":category,"is_moe":moe,"total_parameters_m":total_m,"active_parameters_m":active_m,"selection_parameters_m":active_m if moe else total_m,"parameter_selection_basis":"active_parameters_m" if moe else "total_parameters_m","estimator":estimator,"measurement":"not_measured"}


def validate_estimator_output(source: str, payload: Any) -> dict[str, Any]:
    by_category = {category: [] for category in CATEGORIES}; invalid = []
    for item in _items(payload):
        normalized = normalize_candidate(item, source)
        if normalized is None:
            invalid.append({"model_id":item.get("model_id") or item.get("model") or item.get("id") or item.get("name"),"category":_category(item),"reason":"missing/invalid parameters/category; MoE requires valid active_parameters"})
            continue
        by_category[normalized["category"]].append(normalized)
    counts = {category:len(items) for category,items in by_category.items()}
    valid = all(count == ESTIMATOR_CANDIDATE_COUNT for count in counts.values())
    return {"source":source,"required_candidates_per_category":ESTIMATOR_CANDIDATE_COUNT,"categories":counts,"returned_candidates":sum(counts.values()),"valid":valid,"candidates":by_category,"invalid":invalid}


def select_three_by_parameters(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable=[]; seen=set()
    for item in candidates:
        normalized=normalize_candidate(item,item.get("estimator","unknown"))
        if normalized is None: continue
        key=(_norm(normalized["model_id"]),normalized["category"])
        if key in seen: continue
        seen.add(key); usable.append(normalized)
    usable.sort(key=lambda x:(x["selection_parameters_m"],_norm(x["model_id"]),x["estimator"]))
    if len(usable)<3: return usable
    middle=(len(usable)-1)//2
    return [usable[0],usable[middle],usable[-1]]


def reduce_estimator_outputs(sources: dict[str, Any] | None = None) -> dict[str, Any]:
    sources=sources or {}
    validation={source:validate_estimator_output(source,sources.get(source,{})) for source in SOURCES}
    selected_by_category={}
    for category in CATEGORIES:
        candidates=[]
        for result in validation.values():
            if result["valid"]: candidates.extend(result["candidates"][category])
        selected_by_category[category]=select_three_by_parameters(candidates)
    return {"required_estimators":len(SOURCES),"categories":list(CATEGORIES),"required_per_estimator_per_category":6,"expected_external_candidates":EXPECTED_EXTERNAL_CANDIDATES,"selected_per_category":3,"selected_total":9,"selection_policy":"per category: smallest + lower-middle + largest; Dense=total_parameters_m, MoE=active_parameters_m","validation":validation,"selected":selected_by_category,"measurement":"not_measured"}


def _fit_value(item: dict[str, Any]) -> Any:
    """Read the estimator's real fit field, with explicit legacy aliases."""
    for key in ("fit", "fit_level", "verdict"):
        if key in item and item[key] not in (None, ""):
            return item[key]
    return None


def build_consensus(model_id: str, sources: dict[str, Any] | None = None) -> dict[str, Any]:
    sources=sources or {}; observations={}; values=[]
    for source in SOURCES:
        item=next((x for x in _items(sources.get(source)) if _norm(x.get("model_id") or x.get("model") or x.get("id") or x.get("name"))==_norm(model_id)),None)
        observations[source]=item
        value=_fit_value(item) if item else None
        text=_norm(value)
        if isinstance(value,bool): values.append("fit" if value else "no_fit")
        elif text in {"fit","good","yes","compatible","can run","runs"}: values.append("fit")
        elif text in {"no fit","impossible","cannot","incompatible","no","not compatible","cannot run"}: values.append("no_fit")
    if not values: consensus,status="unknown","METHODOLOGY_GAP"
    elif all(v=="fit" for v in values): consensus,status="fit","AGREE_FIT"
    elif all(v=="no_fit" for v in values): consensus,status="no_fit","AGREE_NO_FIT"
    else: consensus,status="disagreement","FIT_DISAGREEMENT"
    return {"sources":observations,"fit_external":consensus,"fit_consensus":consensus,"disagreement":status,"measurement":"not_measured"}
