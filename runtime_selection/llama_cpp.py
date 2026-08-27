"""Canonical llama.cpp adapter for runtime-selection.v1.1.

This adapter deliberately emits an execution *specification* rather than a
measurement. Command construction remains runner-owned and is not part of the
selection contract.
"""
from __future__ import annotations

from typing import Any

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTER_ID = "llama_cpp.v1"


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    if plan.runtime_id != "llama.cpp":
        raise ValueError(f"llama.cpp adapter received {plan.runtime_id!r}")
    if plan.adapter_id != ADAPTER_ID:
        raise ValueError(f"unexpected llama.cpp adapter id: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id="llama.cpp",
        adapter_id=ADAPTER_ID,
        model_ref=plan.model_ref,
        execution_metadata={
            "execution_mode": "local",
            "runner": "llama.cpp",
            "prepared": True,
        },
    )
