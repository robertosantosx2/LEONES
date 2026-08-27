"""Generic trusted adapter contract for runtime-selection.v1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from scripts.runtime_registry import RuntimeEntry, capability_match


@dataclass(frozen=True)
class RuntimeExecutionSpec:
    runtime_id: str
    adapter_id: str
    model_ref: str
    entrypoint: tuple[str, ...]
    metadata: dict[str, Any]


class RuntimeAdapter:
    """Adapter contract shared by every V1.1 runtime."""

    runtime_id: str
    adapter_id: str

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        if plan.get("runtime", {}).get("name", plan.get("runtime")) != self.runtime_id:
            raise ValueError(f"runtime mismatch for {self.adapter_id}")
        if plan.get("execution_authorized") is not True:
            raise ValueError("runtime plan is not authorized")
        if not plan.get("model_id"):
            raise ValueError("runtime plan has no model identity")
        if not plan.get("quantization"):
            raise ValueError("runtime plan has no quantization")
        architecture = plan.get("architecture_class")
        fmt = plan.get("model_format")
        mode = plan.get("execution_mode")
        backend = plan.get("backend")
        required = set(plan.get("required_capabilities") or [])
        ok, reasons = capability_match(entry, architecture=architecture, model_format=fmt,
                                       mode=mode, backend=backend,
                                       required_capabilities=required)
        if not ok:
            raise ValueError("; ".join(reasons))

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(
            runtime_id=self.runtime_id,
            adapter_id=self.adapter_id,
            model_ref=plan["model_id"],
            entrypoint=tuple(entry.entrypoint["argv"]),
            metadata={"entrypoint_kind": entry.entrypoint["kind"], "metrics": entry.metrics},
        )
