"""RC3 handoff from explicit user selection to runtime-selection.v1.1.

This boundary converts a recorded human choice into a declarative runtime plan.
It does not authorize execution, build shell commands, or create measurements.
"""
from __future__ import annotations

from typing import Any

from .contract import CapabilityMatch, RuntimeSelectionPlan, validate_plan
from .user_selection import validate_selection


def build_runtime_plan(
    selection: dict[str, Any],
    hardware: dict[str, Any],
    *,
    model_ref: str | None = None,
    adapter_id: str = "llama_cpp.v1",
    rationale: list[str] | None = None,
) -> RuntimeSelectionPlan:
    """Build a declarative runtime plan from a validated user selection."""
    validate_selection(selection)
    runtime_id = selection.get("runtime") or "llama.cpp"
    selected = selection["selected_model"]
    ref = model_ref or selected.get("model_id")
    if not ref:
        raise ValueError("selected model has no model_ref")

    plan = RuntimeSelectionPlan(
        runtime_id=runtime_id,
        adapter_id=adapter_id,
        model_ref=ref,
        capability_match=CapabilityMatch(
            architecture=True,
            model_format=True,
            quantization=bool(selected.get("quantization")),
            hardware=True,
            memory=True,
            context=True,
            workload=True,
        ),
        constraints={
            "stack": selection.get("stack"),
            "execution_authorized": False,
            "measurement_authorized": False,
            "consent_required_before_execution": True,
        },
        rationale=rationale or ["runtime plan derived from explicit user selection"],
        selection_metadata={
            "user_selection_schema": selection["schema_version"],
            "selected_model_id": selection["selected_model_id"],
            "stack": selection["stack"],
        },
    )
    validate_plan(plan.to_dict())
    return plan
