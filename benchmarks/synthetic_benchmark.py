#!/usr/bin/env python3
"""Small controlled benchmark used only to exercise the CI evidence path.

This is deliberately not a model-performance benchmark. It measures a fixed
integer workload on the current Python process and labels the result as
synthetic/controlled so it cannot be mistaken for physical model throughput.
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

SCHEMA = "synthetic-benchmark.v1"
BENCHMARK_TYPE = "synthetic/controlled"
ITERATIONS = 100_000


def run(*, iterations: int = ITERATIONS) -> dict[str, Any]:
    """Run a deterministic CPU workload and return bounded CI-safe metrics."""
    if iterations <= 0:
        raise ValueError("iterations must be positive")
    started = time.perf_counter()
    value = 0
    for i in range(iterations):
        value = (value + (i * 31) + 17) % 1_000_003
    elapsed = time.perf_counter() - started
    digest = hashlib.sha256(str(value).encode("ascii")).hexdigest()
    return {
        "schema": SCHEMA,
        "benchmark_type": BENCHMARK_TYPE,
        "iterations": iterations,
        "result": value,
        "result_sha256": digest,
        "wall_seconds": round(elapsed, 6),
        "measurement_scope": "CI synthetic workload only",
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), sort_keys=True))
