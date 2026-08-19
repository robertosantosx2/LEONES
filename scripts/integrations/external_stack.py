"""Common, dependency-free contracts for external stack adapters."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Literal

Status = Literal["PASS", "FAIL", "UNKNOWN"]
Health = Literal["HEALTHY", "DEGRADED", "FAILED", "UNKNOWN"]
EvidenceState = Literal["REPORTED", "UNKNOWN"]
BenchmarkState = Literal["MEASURED", "UNAVAILABLE"]

@dataclass(frozen=True)
class PreflightResult:
    status: Status
    os: str
    architecture: str
    checks: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

@dataclass(frozen=True)
class HealthResult:
    status: Health
    version: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EvidenceResult:
    state: EvidenceState
    product: str
    version: str | None = None
    model: str | None = None
    runtime: str | None = None
    backend: str | None = None
    quantization: str | None = None
    source: str | None = None
    observed_at: str | None = None

@dataclass(frozen=True)
class BenchmarkResult:
    state: BenchmarkState
    tokens_per_second: float | None = None
    command: list[str] = field(default_factory=list)
    raw_output: str = ""
    hardware_id: str | None = None
    runtime: str | None = None


def to_dict(result: Any) -> dict[str, Any]:
    return asdict(result)


def merge_evidence(base: dict[str, Any], evidence: EvidenceResult) -> dict[str, Any]:
    """Merge reported facts only; never manufacture measured values."""
    out = dict(base)
    for key, value in to_dict(evidence).items():
        if value is not None and value != [] and value != {}:
            out[key] = value
    return out
