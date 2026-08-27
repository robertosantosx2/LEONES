"""Trusted runtime adapter boundary.

Selection plans are declarative. Adapters are the only layer allowed to turn a
validated plan into runtime-specific execution details. This module defines
the boundary; concrete runners are added per runtime.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from .contract import RuntimeSelectionPlan, validate_plan


@dataclass(frozen=True)
class ExecutionSpec:
    runtime_id: str
    adapter_id: str
    model_ref: str
    execution_metadata: dict[str, Any]


class RuntimeAdapter(Protocol):
    adapter_id: str

    def prepare(self, plan: RuntimeSelectionPlan) -> ExecutionSpec:
        ...


class DeclarativeAdapter:
    """Safe reference adapter: proves the boundary without executing anything."""

    adapter_id = "reference.v1"

    def prepare(self, plan: RuntimeSelectionPlan) -> ExecutionSpec:
        payload = plan.to_dict()
        validate_plan(payload)
        return ExecutionSpec(
            runtime_id=plan.runtime_id,
            adapter_id=self.adapter_id,
            model_ref=plan.model_ref,
            execution_metadata={"prepared": True},
        )
