"""Build declarative handoff plans for the stack(s) selected by the user."""
from __future__ import annotations

from typing import Any

from .contract import CapabilityMatch, RuntimeSelectionPlan

STACKS = ("magnitude", "ods")


def build_handoffs(selection: dict[str, Any]) -> list[RuntimeSelectionPlan]:
    """Create one plan per selected stack; never executes either stack."""
    model = selection.get("selected_model") or {}
    model_ref = str(selection.get("selected_model_id") or model.get("model_id") or "")
    if not model_ref:
        raise ValueError("selected_model_id is required")

    requested = selection.get("stacks") or []
    if not requested:
        stack = selection.get("stack")
        if stack == "both":
            requested = list(STACKS)
        elif stack in STACKS:
            requested = [stack]
    if not requested or any(stack not in STACKS for stack in requested):
        raise ValueError("select Magnitude, ODS, or both before handoff")

    match = CapabilityMatch(True, True, True, True, True)
    plans: list[RuntimeSelectionPlan] = []
    for stack in dict.fromkeys(requested):
        plans.append(RuntimeSelectionPlan(
            runtime_id=stack,
            adapter_id=f"{stack}.v1.1",
            model_ref=model_ref,
            capability_match=match,
            constraints={"quantization": model.get("quantization"), "consent_required": True},
            rationale=["model selected by Hermes", f"user selected stack: {stack}"],
            selection_metadata={"selector": "hermes", "user_selection_schema": selection.get("schema_version")},
        ))
    return plans
