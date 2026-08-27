"""Ollama adapter boundary for V1.1.

The adapter normalizes Ollama into the common execution-spec boundary. It does
not expose a shell command and does not produce benchmark measurements.
"""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "ollama.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "ollama":
        raise ValueError(f"Ollama adapter received {plan.runtime_id!r}")
    if plan.adapter_id != ADAPTER_ID:
        raise ValueError(f"unexpected Ollama adapter id: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="ollama",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={"execution_mode": "local", "runner": "ollama", "prepared": True},
    )
