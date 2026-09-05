"""RC3 explicit user selection and execution gates.

Recommendations are advisory. This module records an explicit human choice of
model/configuration and one or both execution stacks, but never authorizes
execution or measurement.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "user-selection.v1"
STACKS = {"magnitude", "ods"}
STACK_CHOICES = STACKS | {"both"}


def _validate_stack(stack: str) -> None:
    if stack not in STACK_CHOICES:
        raise ValueError(f"unsupported stack: {stack}")


def _stack_list(stack: str) -> list[str]:
    _validate_stack(stack)
    return ["magnitude", "ods"] if stack == "both" else [stack]


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
    if stack is not None:
        _validate_stack(stack)

    candidate = candidates[model_id]
    stacks = _stack_list(stack) if stack is not None else []
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
        "stacks": stacks,
        "user_choice_required": False,
        "user_choice_recorded": True,
        "user_stack_choice_recorded": bool(stacks),
        "execution_authorized": False,
        "measurement_authorized": False,
        "measured": False,
        "measurement_required": True,
        "consent_required_before_execution": True,
    }


def choose_stack(selection: dict[str, Any], stack: str) -> dict[str, Any]:
    """Add an explicit Magnitude/ODS/both choice while preserving execution gates."""
    if selection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported user-selection schema")
    _validate_stack(stack)
    result = dict(selection)
    result["stack"] = stack
    result["stacks"] = _stack_list(stack)
    result["user_stack_choice_recorded"] = True
    result["execution_authorized"] = False
    result["measurement_authorized"] = False
    result["measured"] = False
    result["consent_required_before_execution"] = True
    return result


def choose_stacks(selection: dict[str, Any], stacks: list[str]) -> dict[str, Any]:
    """Record one or both stack choices for a comparative run."""
    if not stacks or any(stack not in STACKS for stack in stacks):
        raise ValueError("stacks must contain magnitude and/or ods")
    unique = list(dict.fromkeys(stacks))
    return choose_stack(selection, "both" if set(unique) == STACKS else unique[0])


def validate_selection(selection: dict[str, Any]) -> None:
    """Enforce the boundary between human selection and execution."""
    if selection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported user-selection schema")
    if not selection.get("user_choice_recorded"):
        raise ValueError("user model choice is required")
    if not selection.get("selected_model_id"):
        raise ValueError("selected_model_id is required")

    stack = selection.get("stack")
    stacks = selection.get("stacks")
    if stack is None:
        raise ValueError("stack choice is required")
    _validate_stack(stack)
    if not stacks:
        raise ValueError("stack choice is required")
    if any(item not in STACKS for item in stacks):
        raise ValueError("stacks may only contain Magnitude and ODS")
    if stack == "both" and set(stacks) != STACKS:
        raise ValueError("both requires Magnitude and ODS")
    if stack != "both" and stacks != [stack]:
        raise ValueError("stack and stacks disagree")

    if selection.get("execution_authorized") is not False:
        raise ValueError("user selection cannot authorize execution")
    if selection.get("measurement_authorized") is not False:
        raise ValueError("user selection cannot authorize measurement")
    if selection.get("measured") is not False:
        raise ValueError("user selection cannot contain measurements")
