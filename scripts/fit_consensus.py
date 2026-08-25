"""Normalize independent fit estimators and reduce their candidates by category.

Each estimator must return exactly six usable models PER category (text, image,
video). The Selector de LLM keeps three representatives per category: smallest,
lower-middle and largest by total parameter count, normalized to millions (M).
External estimates remain estimates and are never measurements.
"""
from __future__ import annotations
from typing import Any
import re

SOURCES = ("llmfit", "canirun_ai", "localmodel_run", "vrambudget", "llm_checker", "llm_hardware_advisor")
CATEGORIES = ("text", "image", "video")
ESTIMATOR_CANDIDATE_COUNT = 6
SELECTED_REPRESENTATIVE_COUNT = 3


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _items(payload: Any) -> list[dict[str, Any]]:
    items = payload.get("candidates", []) if isinstance(payload, dict) else payload
    return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []


def _category(item: dict[str, Any]) -> str | None:
    value = item.get("category") or item.get("modality") or item.get("type")
    text = _norm(value)
    aliases = {"text": "text", "llm": "text", "language": "text",
               "image": "image", "vision": "image", "multimodal image": "image",
               "video": "video", "video generation": "video", "video model": "video"}
    return aliases.get(text)


def _params_m(item: dict[str, Any]) -> float | None:
    for key in ("parameters_m", "total_params_m", "parameter_count_m", "params_m"):
        value = item.get(key)
        if value not in (None, ""):
            try: return float(value)
            except (TypeError, ValueError): pass
    for key in ("parameters_b", "total_params_b", "parameter_count_b", "params_b"):
        value = item.get(key)
        if value not in (None, ""):
            try: return float(value) * 1000.0
            except (TypeError, ValueError): pass
    for key in ("parameters", "total_params", "parameter_count", "params"):
        value = item.get(key)
        if value in (None, ""): continue
        try: number = float(value)
        except (TypeError, ValueError): continue
        text = str(value).lower()
        if "b" in text: return number * 1000.0
        if "m" in text: return number
        return number / 1_000_000.0 if number >= 1_000_000 else number * 1000.0
    return None


def validate_estimator_output(source: str, payload: Any) -> dict[str, Any]:
    """Require exactly six usable candidates in EACH category."""
    items = _items(payload)
    by_category = {category: [] for category in CATEGORIES}
    invalid = []
    for item in items:
        model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        category = _category(item)
        params_m = _params_m(item)
        if not model_id or category is None or params_m is None:
            invalid.append({"model_id": model_id, "category": category,
                            "reason": "missing model identity, category or parameter count"})
            continue
        by_category[category].append({**item, "model_id": model_id,
                                      "category": category, "parameters_m": params_m})
    counts = {category: len(items) for category, items in by_category.items()}
    valid = all(count == ESTIMATOR_CANDIDATE_COUNT for count in counts.values())
    return {"source": source, "required_candidates_per_category": ESTIMATOR_CANDIDATE_COUNT,
            "categories": counts, "returned_candidates": len(items), "valid": valid,
            "candidates": by_category, "invalid": invalid}


def select_three_by_parameters(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return smallest, lower-middle and largest by total parameters (millions)."""
    usable, seen = [], set()
    for item in candidates:
        model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        params_m = _params_m(item); key = _norm(model_id)
        if not key or params_m is None or key in seen: continue
        seen.add(key); usable.append({**item, "model_id": model_id, "parameters_m": params_m})
    usable.sort(key=lambda x: (x["parameters_m"], _norm(x["model_id"])))
    if not usable: return []
    if len(usable) <= 3: return usable
    middle = (len(usable) - 1) // 2
    return [usable[0], usable[middle], usable[-1]]


def reduce_estimator_outputs(sources: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate 6 models/category/estimator and select 3/category.

    Selection is made from the union of all valid estimator candidates within each
    category. Incomplete estimator/category output is reported and never filled.
    """
    sources = sources or {}
    validation = {source: validate_estimator_output(source, sources.get(source, {})) for source in SOURCES}
    selected_by_category = {}
    for category in CATEGORIES:
        candidates = []
        for source, result in validation.items():
            if result["valid"]:
                candidates.extend({**item, "estimator": source}
                                  for item in result["candidates"][category])
        selected_by_category[category] = select_three_by_parameters(candidates)
    return {
        "required_estimators": len(SOURCES),
        "categories": list(CATEGORIES),
        "required_per_estimator_per_category": ESTIMATOR_CANDIDATE_COUNT,
        "expected_external_candidates": len(SOURCES) * len(CATEGORIES) * ESTIMATOR_CANDIDATE_COUNT,
        "selected_per_category": SELECTED_REPRESENTATIVE_COUNT,
        "selected_total": len(CATEGORIES) * SELECTED_REPRESENTATIVE_COUNT,
        "selection_policy": "per category: smallest + lower-middle + largest by parameters_m",
        "validation": validation,
        "selected": selected_by_category,
        "measurement": "not_measured",
    }


def build_consensus(model_id: str, sources: dict[str, Any] | None = None) -> dict[str, Any]:
    sources = sources or {}; observations = {}; values = []
    for source in SOURCES:
        item = next((x for x in _items(sources.get(source))
                     if _norm(x.get("model_id") or x.get("model") or x.get("id") or x.get("name")) == _norm(model_id)), None)
        observations[source] = item
        value = item.get("fit") if item else None
        text = _norm(value)
        if isinstance(value, bool): values.append("fit" if value else "no_fit")
        elif text in {"fit", "good", "yes", "compatible", "can run", "runs"}: values.append("fit")
        elif text in {"no fit", "impossible", "cannot", "incompatible", "no"}: values.append("no_fit")
    if not values: consensus, status = "unknown", "METHODOLOGY_GAP"
    elif all(v == "fit" for v in values): consensus, status = "fit", "AGREE_FIT"
    elif all(v == "no_fit" for v in values): consensus, status = "no_fit", "AGREE_NO_FIT"
    else: consensus, status = "disagreement", "FIT_DISAGREEMENT"
    return {"sources": observations, "fit_external": consensus, "fit_consensus": consensus,
            "disagreement": status, "measurement": "not_measured"}
