"""Deterministic fake runner for runtime-selection.v1.1 contract tests.

This fixture is intentionally not a runtime implementation. It accepts the
adapter-produced ExecutionSpec and returns observed execution facts so the
real benchmark boundary can be exercised in CI without a model or GPU.
"""
from __future__ import annotations

from typing import Any

from runtime_selection.adapters import ExecutionSpec


def run(spec: ExecutionSpec, *, tokens_generated: int = 40, elapsed_seconds: float = 4.0) -> dict[str, Any]:
    if not spec.execution_metadata.get("prepared"):
        raise ValueError("fixture runner requires a prepared ExecutionSpec")
    if tokens_generated <= 0 or elapsed_seconds <= 0:
        raise ValueError("fixture execution facts must be positive")

    return {
        "execution_id": "fixture-exec-001",
        "runtime_id": spec.runtime_id,
        "adapter_id": spec.adapter_id,
        "model_ref": spec.model_ref,
        "tokens_generated": tokens_generated,
        "elapsed_seconds": elapsed_seconds,
    }


__all__ = ["run"]
