"""Runtime-benchmark.v1 execution boundary.

The benchmark consumes an execution result produced by a runner. It is the
only layer in this path that derives measured performance from observed
execution facts. It never selects a runtime and never resolves commands.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "runtime-benchmark.v1"


@dataclass(frozen=True)
class BenchmarkMeasurement:
    execution_id: str
    runtime_id: str
    model_ref: str
    tokens_generated: int
    elapsed_seconds: float

    @property
    def measured_tps(self) -> float:
        if self.tokens_generated <= 0:
            raise ValueError("tokens_generated must be positive")
        if self.elapsed_seconds <= 0:
            raise ValueError("elapsed_seconds must be positive")
        return self.tokens_generated / self.elapsed_seconds

    def to_result(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "evidence": {
                "evidence_type": "measured",
                "execution_id": self.execution_id,
                "source": "runtime-benchmark.v1",
            },
            "model": {"id": self.model_ref},
            "hardware": {},
            "agentic": {
                "execution_id": self.execution_id,
                "runtime": {"name": self.runtime_id},
                "metrics": {
                    "tokens_generated": self.tokens_generated,
                    "runtime_wall_seconds": self.elapsed_seconds,
                    "measured_tps": self.measured_tps,
                },
            },
        }


def measure(execution: dict[str, Any]) -> BenchmarkMeasurement:
    """Convert observed runner facts into a measured benchmark result."""
    execution_id = execution.get("execution_id")
    runtime_id = execution.get("runtime_id")
    model_ref = execution.get("model_ref")
    tokens_generated = execution.get("tokens_generated")
    elapsed_seconds = execution.get("elapsed_seconds")

    if not execution_id:
        raise ValueError("execution_id is required")
    if not runtime_id or not model_ref:
        raise ValueError("runtime_id and model_ref are required")
    if isinstance(tokens_generated, bool) or not isinstance(tokens_generated, int):
        raise ValueError("tokens_generated must be an integer")
    if tokens_generated <= 0:
        raise ValueError("tokens_generated must be positive")
    if isinstance(elapsed_seconds, bool) or not isinstance(elapsed_seconds, (int, float)):
        raise ValueError("elapsed_seconds must be numeric")
    if elapsed_seconds <= 0:
        raise ValueError("elapsed_seconds must be positive")

    return BenchmarkMeasurement(
        execution_id=execution_id,
        runtime_id=runtime_id,
        model_ref=model_ref,
        tokens_generated=tokens_generated,
        elapsed_seconds=float(elapsed_seconds),
    )


__all__ = ["BenchmarkMeasurement", "SCHEMA_VERSION", "measure"]
