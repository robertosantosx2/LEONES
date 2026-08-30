"""Dependency-free ODS adapter boundary.

No installation, service startup or external command is performed here.
"""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "ods.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "ods":
        raise ValueError(f"ODS adapter received {plan.runtime_id!r}")
    if plan.adapter_id != ADAPTER_ID:
        raise ValueError(f"unexpected ODS adapter id: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="ods",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={"execution_mode": "local-stack", "prepared": True},
    )
