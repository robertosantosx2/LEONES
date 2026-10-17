"""Adapter boundary between a selected runtime plan and Agentic Benchmark V1.

The adapter never executes arbitrary model output. A concrete backend implements
`prepare` and `invoke`; the benchmark runner owns tracing, budgets and result
provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class RuntimePlan:
    model_id: str
    runtime: str
    quantization: str
    selection_status: str
    execution_authorized: bool
    measurement_required: bool
    estimated_tps: float | None = None


class ModelRuntimeAdapter(Protocol):
    name: str

    def prepare(self, plan: RuntimePlan) -> dict[str, Any]: ...

    def invoke(self, prompt: str, *, tools: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]: ...


def from_runtime_plan(plan: dict[str, Any]) -> RuntimePlan:
    """Validate and normalize the output of `scripts.runtime_gate`."""
    required = ("model_id", "runtime", "quantization", "selection_status")
    missing = [key for key in required if not plan.get(key)]
    if missing:
        raise ValueError(f"runtime plan missing fields: {', '.join(missing)}")
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not execution-authorized")
    if plan.get("measurement_required") is not True:
        raise ValueError("runtime plan must require measurement")
    return RuntimePlan(
        model_id=str(plan["model_id"]),
        runtime=str(plan["runtime"]),
        quantization=str(plan["quantization"]),
        selection_status=str(plan["selection_status"]),
        execution_authorized=True,
        measurement_required=True,
        estimated_tps=plan.get("estimated_tps"),
    )
