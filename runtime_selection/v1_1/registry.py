"""Runtime Registry V1.1 capability matching.

This module intentionally contains no runtime-specific commands. Concrete
entrypoints are resolved by trusted adapters after a selection is authorized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


BLOCKED_REASONS = {
    "runtime_unknown",
    "runtime_unavailable",
    "plan_unauthorized",
    "entrypoint_untrusted",
    "incompatible_model",
    "incompatible_format",
    "incompatible_hardware",
    "incompatible_execution_mode",
}


@dataclass(frozen=True)
class MatchResult:
    runtime_id: str
    allowed: bool
    reasons: tuple[str, ...] = ()


def index_registry(registry: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    """Return runtime entries keyed by runtime_id, rejecting duplicates."""
    runtimes = registry.get("runtimes", [])
    index: dict[str, Mapping[str, Any]] = {}
    for runtime in runtimes:
        runtime_id = runtime["runtime_id"]
        if runtime_id in index:
            raise ValueError(f"duplicate runtime_id: {runtime_id}")
        index[runtime_id] = runtime
    return index


def match_runtime(
    runtime: Mapping[str, Any],
    *,
    model_architecture: str,
    model_format: str,
    hardware_accelerator: str,
    memory_gb: float,
    execution_mode: str,
    authorized: bool,
    trusted_entrypoint: bool,
) -> MatchResult:
    """Match a selected model/workload against one registry entry.

    This function only evaluates declarative capabilities. It never resolves
    or executes an entrypoint and never returns a performance measurement.
    """
    reasons: list[str] = []

    if not authorized:
        reasons.append("plan_unauthorized")
    if not trusted_entrypoint:
        reasons.append("entrypoint_untrusted")

    availability = runtime.get("availability", {}).get("status")
    if availability != "available":
        reasons.append("runtime_unavailable")

    if model_architecture not in runtime.get("architectures", []):
        reasons.append("incompatible_model")
    if model_format not in runtime.get("formats", []):
        reasons.append("incompatible_format")

    hardware = runtime.get("hardware", {})
    accelerators = hardware.get("accelerators", [])
    if hardware_accelerator not in accelerators:
        reasons.append("incompatible_hardware")

    minimum_gb = hardware.get("memory", {}).get("minimum_gb", 0)
    if memory_gb < minimum_gb:
        reasons.append("incompatible_hardware")

    if execution_mode not in runtime.get("execution_modes", []):
        reasons.append("incompatible_execution_mode")

    return MatchResult(
        runtime_id=runtime["runtime_id"],
        allowed=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def select_candidates(
    registry: Mapping[str, Any],
    *,
    model_architecture: str,
    model_format: str,
    hardware_accelerator: str,
    memory_gb: float,
    execution_mode: str,
    authorized: bool,
    trusted_entrypoints: set[str],
) -> tuple[MatchResult, ...]:
    """Return capability matches without exposing or resolving commands."""
    candidates: list[MatchResult] = []
    for runtime in registry.get("runtimes", []):
        candidates.append(
            match_runtime(
                runtime,
                model_architecture=model_architecture,
                model_format=model_format,
                hardware_accelerator=hardware_accelerator,
                memory_gb=memory_gb,
                execution_mode=execution_mode,
                authorized=authorized,
                trusted_entrypoint=runtime.get("entrypoint_ref") in trusted_entrypoints,
            )
        )
    return tuple(candidates)
