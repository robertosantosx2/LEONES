"""AirLLM adapter boundary.

V1.1 promotes AirLLM from knowledge candidate to an executable-runtime
candidate without claiming that execution has happened. A concrete runner is
responsible for environment/model availability checks.
"""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "airllm.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "AirLLM" or plan.adapter_id != ADAPTER_ID:
        raise ValueError("invalid AirLLM adapter selection")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="AirLLM",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={"execution_mode": "local", "runner": "airllm", "prepared": True},
    )
