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

    @property
    def execution_metadata(self) -> dict[str, Any]:
        return self.metadata

class RuntimeAdapter:
    """Adapter contract shared by every V1.1 runtime."""
    runtime_id: str
    adapter_id: str

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        runtime_value = plan.get("runtime")
        selected_runtime = runtime_value.get("name") if isinstance(runtime_value, dict) else runtime_value
        if selected_runtime != self.runtime_id: raise ValueError(f"runtime mismatch for {self.adapter_id}")
        if plan.get("execution_authorized") is not True: raise ValueError("runtime plan is not authorized")
        if not plan.get("model_id"): raise ValueError("runtime plan has no model identity")
        if not plan.get("quantization"): raise ValueError("runtime plan has no quantization")
        ok, reasons = capability_match(entry, architecture=plan.get("architecture_class"), model_format=plan.get("model_format"),
                                       mode=plan.get("execution_mode"), backend=plan.get("backend"),
                                       required_capabilities=set(plan.get("required_capabilities") or []))
        if not ok: raise ValueError("; ".join(reasons))

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(self.runtime_id, self.adapter_id, plan["model_id"], tuple(entry.entrypoint["argv"]),
                                    {"entrypoint_kind": entry.entrypoint["kind"], "metrics": entry.metrics})
