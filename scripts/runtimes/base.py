"""Generic trusted adapter contract for runtime-selection.v1."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from scripts.runtime_registry import RuntimeEntry, capability_match, validate_entrypoint

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
    """Adapter contract shared by every V1.1 runtime.

    Adapters are deliberately declarative. They may validate and prepare an
    execution specification, but they never execute a runtime themselves.
    """
    runtime_id: str
    adapter_id: str

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        runtime_value = plan.get("runtime")
        selected_runtime = runtime_value.get("name") if isinstance(runtime_value, dict) else runtime_value
        selected_adapter = runtime_value.get("adapter") if isinstance(runtime_value, dict) else None
        if selected_runtime != self.runtime_id:
            raise ValueError(f"runtime mismatch for {self.adapter_id}")
        if selected_adapter is not None and selected_adapter != self.adapter_id:
            raise ValueError(f"adapter mismatch for {self.runtime_id}")
        if not plan.get("model_id"):
            raise ValueError("runtime plan has no model identity")
        if not plan.get("quantization"):
            raise ValueError("runtime plan has no quantization")
        validate_entrypoint(entry)
        if entry.id != self.runtime_id:
            raise ValueError(f"registry runtime mismatch for {self.runtime_id}")
        if entry.adapter != self.adapter_id:
            raise ValueError(f"registry adapter mismatch for {self.runtime_id}")
        ok, reasons = capability_match(
            entry,
            architecture=plan.get("architecture_class"),
            model_format=plan.get("model_format"),
            mode=plan.get("execution_mode"),
            backend=plan.get("backend"),
            required_capabilities=set(plan.get("required_capabilities") or []),
        )
        if not ok:
            raise ValueError("; ".join(reasons))

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(
            self.runtime_id,
            self.adapter_id,
            plan["model_id"],
            tuple(entry.entrypoint["argv"]),
            {
                "entrypoint_kind": entry.entrypoint["kind"],
                "metrics": entry.metrics,
                "host_requirements": entry.host_requirements,
                "physical_test_required": entry.physical_test_required,
            },
        )
