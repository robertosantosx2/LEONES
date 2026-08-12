"""Stable data contracts between Atlas, Router, Agents and Runtime.

The first implementation deliberately contains no backend-specific code.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HardwareProfile:
    cpu: str
    ram_gb: float
    gpu: str | None = None
    vram_gb: float | None = None
    npu: str | None = None
    os: str | None = None
    architecture: str | None = None
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class TaskRequirements:
    task_type: str
    context_tokens: int | None = None
    required_tools: tuple[str, ...] = ()
    latency_target_s: float | None = None
    quality_priority: float = 0.5
    memory_limit_gb: float | None = None


@dataclass(frozen=True)
class ModelCandidate:
    model_id: str
    revision: str | None = None
    quantization: str | None = None
    formats: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteDecision:
    model_id: str
    quantization: str | None
    backend: str
    device: str
    parameters: dict[str, Any] = field(default_factory=dict)
    rationale: tuple[str, ...] = ()


@dataclass(frozen=True)
class BenchmarkResult:
    experiment_id: str
    model_id: str
    backend: str
    tokens_per_second: float | None = None
    prompt_tokens_per_second: float | None = None
    memory_gb: float | None = None
    task_success: bool | None = None
    task_seconds: float | None = None
    status: str = "reported"
