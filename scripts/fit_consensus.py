"""Normalize independent fit estimators and reduce their candidates deterministically.

External estimates remain estimates. Parameter counts are represented in millions
of parameters and are never treated as measured performance.
"""
from __future__ import annotations
from typing import Any
import re

SOURCES = ("llmfit", "canirun_ai", "localmodel_run", "vrambudget", "llm_checker", "llm_hardware_advisor")
ESTIMATOR_CANDIDATE_COUNT = 6
SELECTED_REPRESENTATIVE_COUNT = 3


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _items(payload: Any) -> list[dict[str, Any]]:
    items = payload.get("candidates", []) if isinstance(payload, dict) else payload
    return [x for x in items if isinstance(x, dict)] if isinstance(items, list) else []


def _match(payload: Any, model_id: str) -> dict[str, Any] | None:
    target = _norm(model_id)
    for item in _items(payload):
        ident = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        if ident and _norm(ident) == target:
            return item
    return None


def _fit_value(item: dict[str, Any] | None) -> str | None:
    if not item:
        return None
    value = item.get("fit") or item.get("fit_level") or item.get("compatibility") or item.get("verdict")
    if isinstance(value, bool):
        return "fit" if value else "no_fit"
    text = _norm(value)
    if text in {"fit", "good", "yes", "compatible", "can run", "runs"}:
        return "fit"
    if text in {"no fit", "impossible", "cannot", "incompatible", "no"}:
        return "no_fit"
    return "unknown" if value is not None else None


def _params_m(item: dict[str, Any]) -> float | None:
    """Read total parameter count and normalize it to millions (M)."""
    for key in ("parameters_m", "total_params_m", "parameter_count_m", "params_m"):
        value = item.get(key)
        if value not in (None, ""):
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
    for key in ("parameters_b", "total_params_b", "parameter_count_b", "params_b"):
        value = item.get(key)
        if value not in (None, ""):
            try:
                return float(value) * 1000.0
            except (TypeError, ValueError):
                pass
    for key in ("parameters", "total_params", "parameter_count", "params"):
        value = item.get(key)
        if value in (None, ""):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        # Explicitly labelled strings are respected; bare values use the common
        # convention that B means billions and M means millions.
        text = str(value).lower()
        if "b" in text:
            return number * 1000.0
        if "m" in text:
            return number
        return number / 1_000_000.0 if number >= 1_000_000 else number * 1000.0
    return None


def validate_estimator_output(source: str, payload: Any) -> dict[str, Any]:
    """Require exactly six usable candidates from each estimator."""
    items = _items(payload)
    valid = []
    invalid = []
    for item in items:
        model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        params_m = _params_m(item)
        if model_id and params_m is not None:
            valid.append({**item, "model_id": model_id, "parameters_m": params_m})
        else:
            invalid.append({"model_id": model_id, "reason": "missing model identity or parameter count"})
    return {
        "source": source,
        "required_candidates": ESTIMATOR_CANDIDATE_COUNT,
        "returned_candidates": len(items),
        "usable_candidates": len(valid),
        "valid": len(valid) == ESTIMATOR_CANDIDATE_COUNT,
        "candidates": valid[:ESTIMATOR_CANDIDATE_COUNT],
        "invalid": invalid,
    }


def select_three_by_parameters(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return smallest, middle and largest model by total parameters (millions).

    The middle candidate is the lower-middle element for an even-sized pool,
    making the rule deterministic. Ties are resolved by model id.
    """
    usable = []
    seen: set[str] = set()
    for item in candidates:
        model_id = item.get("model_id") or item.get("model") or item.get("id") or item.get("name")
        params_m = _params_m(item)
        key = _norm(model_id)
        if not key or params_m is None or key in seen:
            continue
        seen.add(key)
        usable.append({**item, "model_id": model_id, "parameters_m": params_m})
    usable.sort(key=lambda x: (x["parameters_m"], _norm(x["model_id"])))
    if not usable:
        return []
    if len(usable) <= 3:
        return usable
    middle = (len(usable) - 1) // 2
    indices = [0, middle, len(usable) - 1]
    return [usable[i] for i in indices]


def reduce_estimator_outputs(sources: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate six candidates/source and select three span representatives.

    Selection is made from the union of all valid estimator candidates. If any
    estimator does not provide exactly six usable candidates, the result is
    marked incomplete rather than silently filling or fabricating candidates.
    """
    sources = sources or {}
    validation = {source: validate_estimator_output(source, sources.get(source, {})) for source in SOURCES}
    all_candidates = []
    for source, result in validation.items():
        for item in result["candidates"]:
            all_candidates.append({**item, "estimator": source})
    selected = select_three_by_parameters(all_candidates)
    return {
        "required_per_estimator": ESTIMATOR_CANDIDATE_COUNT,
        "estimator_count": len(SOURCES),
        "total_expected_candidates": ESTIMATOR_CANDIDATE_COUNT * len(SOURCES),
        "validation": validation,
        "selection_policy": "smallest + lower-middle + largest by parameters_m",
        "selected_count": len(selected),
        "selected": selected,
        "measurement": "not_measured",
    }


def build_consensus(model_id: str, sources: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return source-by-source estimates plus a conservative fit consensus."""
    sources = sources or {}
    observations: dict[str, Any] = {}
    values: list[str] = []
    for source in SOURCES:
        item = _match(sources.get(source), model_id)
        value = _fit_value(item)
        observations[source] = item
        if value in {"fit", "no_fit"}:
            values.append(value)
    if not values:
        consensus, status = "unknown", "METHODOLOGY_GAP"
    elif all(v == "fit" for v in values):
        consensus, status = "fit", "AGREE_FIT"
    elif all(v == "no_fit" for v in values):
        consensus, status = "no_fit", "AGREE_NO_FIT"
    else:
        consensus, status = "disagreement", "FIT_DISAGREEMENT"
    return {
        "sources": observations,
        "fit_external": consensus,
        "fit_consensus": consensus,
        "disagreement": status,
        "measurement": "not_measured",
    }
