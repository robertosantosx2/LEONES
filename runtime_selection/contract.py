"""Declarative runtime-selection.v1.1 contract.

The contract deliberately contains no shell command, argv, executable path,
or performance measurement. Commands belong to trusted adapters/runners and
measurements belong exclusively to runtime-benchmark.v1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SCHEMA_VERSION = "runtime-selection.v1.1"


@dataclass(frozen=True)
class CapabilityMatch:
    architecture: bool
    model_format: bool
    quantization: bool
    hardware: bool
    memory: bool
    context: bool = True
    workload: bool = True

    @property
    def compatible(self) -> bool:
        return all((self.architecture, self.model_format, self.quantization,
                    self.hardware, self.memory, self.context, self.workload))

    def to_dict(self) -> dict[str, bool]:
        return {
            "architecture": self.architecture,
            "model_format": self.model_format,
            "quantization": self.quantization,
            "hardware": self.hardware,
            "memory": self.memory,
            "context": self.context,
            "workload": self.workload,
            "compatible": self.compatible,
        }


@dataclass(frozen=True)
class RuntimeSelectionRequest:
    model: dict[str, Any]
    hardware: dict[str, Any]
    workload: dict[str, Any] = field(default_factory=dict)
    objective: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "model": self.model,
            "hardware": self.hardware,
            "workload": self.workload,
            "objective": self.objective,
        }


@dataclass(frozen=True)
class RuntimeSelectionPlan:
    runtime_id: str
    adapter_id: str
    model_ref: str
    capability_match: CapabilityMatch
    constraints: dict[str, Any] = field(default_factory=dict)
    rationale: list[str] = field(default_factory=list)
    selection_metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.runtime_id or not self.adapter_id or not self.model_ref:
            raise ValueError("runtime_id, adapter_id and model_ref are required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "runtime_id": self.runtime_id,
            "adapter_id": self.adapter_id,
            "model_ref": self.model_ref,
            "capability_match": self.capability_match.to_dict(),
            "constraints": self.constraints,
            "rationale": self.rationale,
            "selection_metadata": self.selection_metadata,
        }


def validate_plan(payload: dict[str, Any]) -> None:
    """Reject execution details and measured performance from a selection plan."""
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported runtime-selection schema")
    forbidden = {"command", "argv", "shell", "executable", "tokens_per_second", "measured_tps"}
    leaked = forbidden.intersection(payload)
    if leaked:
        raise ValueError(f"selection plan contains execution/measurement fields: {sorted(leaked)}")
    if "runtime_id" not in payload or "adapter_id" not in payload or "model_ref" not in payload:
        raise ValueError("selection plan is missing required identity fields")
