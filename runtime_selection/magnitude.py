"""Dependency-free Magnitude adapter boundary.

The adapter prepares metadata only. Agent execution and measurement remain
owned by the existing runner and benchmark/evidence contracts.
"""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "magnitude.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "magnitude":
        raise ValueError(f"Magnitude adapter received {plan.runtime_id!r}")
    if plan.adapter_id != ADAPTER_ID:
        raise ValueError(f"unexpected Magnitude adapter id: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="magnitude",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={"execution_mode": "agent", "prepared": True},
    )
