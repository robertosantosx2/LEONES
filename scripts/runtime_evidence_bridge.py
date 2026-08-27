"""Bridge from runtime-benchmark.v1 to the existing evidence boundary."""

from __future__ import annotations
from typing import Any


def to_evidence(benchmark: dict[str, Any]) -> dict[str, Any]:
    if benchmark.get("schema_version") != "runtime-benchmark.v1":
        raise ValueError("unsupported benchmark artifact")
    if benchmark.get("measurement_status") != "measured" or not benchmark.get(
        "measured"
    ):
        raise ValueError(
            "only completed measured benchmark artifacts can become runtime evidence"
        )
    if not benchmark.get("execution_id") or not benchmark.get("finished_at"):
        raise ValueError("measured benchmark lacks execution provenance")
    if (
        not benchmark.get("runtime")
        or not benchmark.get("adapter")
        or not benchmark.get("model_id")
    ):
        raise ValueError("measured benchmark lacks execution identity")
    measured = benchmark["measured"]
    if "estimated_tps" in measured:
        raise ValueError("estimated performance cannot become evidence measurement")
    if not any(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in measured.values()
    ):
        raise ValueError("runtime evidence requires a numeric measured fact")
    return {
        "kind": "runtime-measurement",
        "status": "measured",
        "execution_id": benchmark["execution_id"],
        "measured_at": benchmark["finished_at"],
        "runtime": benchmark["runtime"],
        "adapter": benchmark["adapter"],
        "runtime_version": benchmark.get("runtime_version"),
        "model": benchmark.get("model"),
        "model_id": benchmark.get("model_id"),
        "quantization": benchmark.get("quantization"),
        "hardware": benchmark.get("hardware", {}),
        "workload": benchmark.get("workload", {}),
        "protocol": benchmark.get("protocol", {}),
        "measurements": measured,
        "provenance": {
            "source": "LEONES",
            "kind": "observed-runtime-execution",
            "execution_id": benchmark["execution_id"],
        },
    }
