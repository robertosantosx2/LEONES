"""RC3 explicit user selection and execution gates.

Recommendations are advisory. This module records an explicit human choice of
model/configuration and stack, but never authorizes execution or measurement.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "user-selection.v1"
STACKS = {"magnitude", "ods"}


def create_selection(
    decision: dict[str, Any],
    model_id: str,
    *,
    quantization: str | None = None,
    runtime: str = "llama.cpp",
    stack: str | None = None,
) -> dict[str, Any]:
    """Record a user's explicit model/config choice without authorizing execution."""
    candidates = {c.get("model_id"): c for c in decision.get("candidates", [])}
    if model_id not in candidates:
        raise ValueError(f"model is not present in decision candidates: {model_id}")
    if stack is not None and stack not in STACKS:
        raise ValueError(f"unsupported stack: {stack}")

    candidate = candidates[model_id]
    return {
        "schema_version": SCHEMA_VERSION,
        "decision_profile": decision.get("profile"),
        "recommended_model_id": decision.get("recommended_model_id"),
        "selected_model_id": model_id,
        "selected_model": {
            "model_id": model_id,
            "name": candidate.get("name", model_id),
            "revision": candidate.get("revision"),
            "quantization": quantization or candidate.get("quantization"),
        },
        "runtime": runtime,
        "stack": stack,
        "user_choice_required": False,
        "user_choice_recorded": True,
        "execution_authorized": False,
        "measurement_authorized": False,
        "measured": False,
        "measurement_required": True,
        "consent_required_before_execution": True,
    }


def choose_stack(selection: dict[str, Any], stack: str) -> dict[str, Any]:
    """Add an explicit Magnitude/ODS choice while preserving execution gates."""
    if selection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported user-selection schema")
    if stack not in STACKS:
        raise ValueError(f"unsupported stack: {stack}")
    result = dict(selection)
    result["stack"] = stack
    result["user_stack_choice_recorded"] = True
    result["execution_authorized"] = False
    result["measurement_authorized"] = False
    result["consent_required_before_execution"] = True
    return result


def validate_selection(selection: dict[str, Any]) -> None:
    """Enforce the boundary between human selection and execution."""
    if selection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported user-selection schema")
    if not selection.get("user_choice_recorded"):
        raise ValueError("user model choice is required")
    if not selection.get("selected_model_id"):
        raise ValueError("selected_model_id is required")
    if selection.get("stack") not in STACKS:
        raise ValueError("explicit Magnitude or ODS stack choice is required")
    if selection.get("execution_authorized") is not False:
        raise ValueError("user selection cannot authorize execution")
    if selection.get("measurement_authorized") is not False:
        raise ValueError("user selection cannot authorize measurement")
    if selection.get("measured") is not False:
        raise ValueError("user selection cannot contain measurements")
