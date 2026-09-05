"""Build declarative handoff plans for the stack(s) selected by the user."""
from __future__ import annotations

from typing import Any

from .contract import CapabilityMatch, RuntimeSelectionPlan

STACKS = ("magnitude", "ods")


def build_handoffs(selection: dict[str, Any]) -> list[RuntimeSelectionPlan]:
    """Create one plan per explicitly selected stack; never executes either stack."""
    model = selection.get("selected_model") or {}
    model_ref = str(selection.get("selected_model_id") or model.get("model_id") or "")
    if not model_ref:
        raise ValueError("selected_model_id is required")

    stack = selection.get("stack")
    requested = selection.get("stacks")
    if stack is None or not requested:
        raise ValueError("select Magnitude, ODS, or both before handoff")
    if stack == "both":
        if set(requested) != set(STACKS):
            raise ValueError("both requires Magnitude and ODS before handoff")
    elif stack in STACKS:
        if requested != [stack]:
            raise ValueError("stack and stacks disagree")
    else:
        raise ValueError("unsupported stack choice")
    if any(item not in STACKS for item in requested):
        raise ValueError("select Magnitude, ODS, or both before handoff")

    match = CapabilityMatch(True, True, True, True, True)
    plans: list[RuntimeSelectionPlan] = []
    for selected_stack in dict.fromkeys(requested):
        plans.append(RuntimeSelectionPlan(
            runtime_id=selected_stack,
            adapter_id=f"{selected_stack}.v1.1",
            model_ref=model_ref,
            capability_match=match,
            constraints={"quantization": model.get("quantization"), "consent_required": True},
            rationale=["model selected by Hermes", f"user selected stack: {selected_stack}"],
            selection_metadata={"selector": "hermes", "user_selection_schema": selection.get("schema_version")},
        ))
    return plans
