"""Normalize independent fit estimators without turning estimates into measurements."""
from __future__ import annotations
from typing import Any
import re

SOURCES = ("llmfit", "canirun_ai", "localmodel_run", "vrambudget", "llm_checker", "llm_hardware_advisor")


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _match(payload: Any, model_id: str) -> dict[str, Any] | None:
    items = payload.get("candidates", []) if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        return None
    target = _norm(model_id)
    for item in items:
        if not isinstance(item, dict):
            continue
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
    if text in {"no fit", "no fit", "impossible", "cannot", "incompatible", "no"}:
        return "no_fit"
    return "unknown" if value is not None else None


def build_consensus(model_id: str, sources: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return source-by-source estimates plus a conservative consensus.

    Consensus is descriptive only. It must never be used as a measured result.
    """
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
        consensus = "unknown"
        status = "METHODOLOGY_GAP"
    elif all(v == "fit" for v in values):
        consensus = "fit"
        status = "AGREE_FIT"
    elif all(v == "no_fit" for v in values):
        consensus = "no_fit"
        status = "AGREE_NO_FIT"
    else:
        consensus = "disagreement"
        status = "FIT_DISAGREEMENT"
    return {
        "sources": observations,
        "fit_external": consensus,
        "fit_consensus": consensus,
        "disagreement": status,
        "measurement": "not_measured",
    }
