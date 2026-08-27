"""FreeToken adapter boundary; eligibility remains a separate gate."""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "freetoken.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "FreeToken" or plan.adapter_id != ADAPTER_ID:
        raise ValueError("invalid FreeToken adapter selection")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="FreeToken",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={"execution_mode": "local", "runner": "freetoken", "gate_required": True, "prepared": True},
    )
