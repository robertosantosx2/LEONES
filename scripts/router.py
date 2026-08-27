#!/usr/bin/env python3
"""Canonical read-only Router for LEONES recommendations."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ALLOWED_MODES = {"OPEN_ALL", "FORCE_COPYLEFT_CHECK"}


def route_recommendation(
    recommendation: dict[str, Any], *, osi_mode: str = "OPEN_ALL"
) -> dict[str, Any]:
    """Validate and expose a recommendation without mutating canonical knowledge."""
    if osi_mode not in ALLOWED_MODES:
        raise ValueError("unsupported osi_mode")
    if not isinstance(recommendation, dict):
        raise ValueError("recommendation must be an object")
    evidence_refs = recommendation.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError("recommendation requires evidence_refs")
    if any(not isinstance(ref, str) or not ref.strip() for ref in evidence_refs):
        raise ValueError("evidence_refs must contain non-empty strings")
    if recommendation.get("action") in {
        "ATLAS_WRITE",
        "WRITE_KNOWLEDGE",
        "DELETE_KNOWLEDGE",
    }:
        raise ValueError("Router is read-only")

    result = deepcopy(recommendation)
    result["router"] = {
        "schema_version": "1.0",
        "osi_mode": osi_mode,
        "read_only": True,
        "knowledge_write": False,
        "evidence_traceable": True,
    }
    return result


__all__ = ["route_recommendation"]
