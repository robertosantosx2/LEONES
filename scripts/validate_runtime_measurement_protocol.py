#!/usr/bin/env python3
"""Validate semantic invariants that JSON Schema cannot express conveniently."""
from __future__ import annotations

import json
import sys
from pathlib import Path


REQUIRED = {
    "schema",
    "protocol_id",
    "protocol_version",
    "state",
    "objective",
    "workload",
    "execution",
    "metrics",
    "environment",
    "provenance",
    "acceptance",
}


def fail(message: str) -> None:
    raise SystemExit(f"INVALID: {message}")


def validate(doc: dict) -> None:
    missing = REQUIRED - set(doc)
    if missing:
        fail(f"missing top-level fields: {sorted(missing)}")
    if doc["schema"] != "runtime-measurement-protocol.v1":
        fail("unexpected schema")
    if doc["protocol_version"] != "1.0":
        fail("unsupported protocol version")

    workload = doc["workload"]
    model = workload["model"]
    if not model.get("id") or not model.get("revision") or not model.get("artifact"):
        fail("model identity must be pinned")
    if not model.get("quantization"):
        fail("quantization must be explicit")

    execution = doc["execution"]
    if execution["measurement_runs"] < execution["warmup_runs"] * 0 + 1:
        fail("measurement_runs must be >= 1")
    if doc["acceptance"]["minimum_successful_runs"] > execution["measurement_runs"]:
        fail("minimum_successful_runs cannot exceed measurement_runs")
    if doc["acceptance"]["require_exit_code_zero"] is not True:
        fail("exit-code-zero requirement cannot be disabled")
    if doc["acceptance"]["require_raw_stdout_stderr"] is not True:
        fail("raw stdout/stderr preservation cannot be disabled")
    if doc["acceptance"]["require_artifact_hash"] is not True:
        fail("artifact hashing cannot be disabled")
    if doc["acceptance"].get("allow_partial_results", False) is not False:
        fail("partial results cannot be accepted")

    metrics = doc["metrics"]
    if metrics["primary"] not in metrics["required"] and metrics["primary"] not in {
        "decode_tokens_per_second", "end_to_end_tokens_per_second", "ttft_ms"
    }:
        fail("primary metric is not declared")

    required_metrics = set(metrics["required"])
    if "decode_tokens_per_second" in required_metrics:
        if "generation_time_ms" not in required_metrics or "output_tokens" not in required_metrics:
            fail("decode TPS requires generation_time_ms and output_tokens")
    if "ttft_ms" in required_metrics and "total_time_ms" not in required_metrics:
        fail("TTFT series must preserve total_time_ms")

    command = doc["environment"].get("command", [])
    if not command or any(not isinstance(part, str) for part in command):
        fail("runtime command must be a non-empty argv array")

    if doc["state"] == "frozen" and doc["provenance"].get("protocol_sha256") is None:
        print(
            "WARNING: frozen protocol has no protocol_sha256; "
            "populate it after canonical serialization.",
            file=sys.stderr,
        )


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {Path(sys.argv[0]).name} PROTOCOL.json", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: cannot read JSON: {exc}", file=sys.stderr)
        return 1
    try:
        validate(doc)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"VALID: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
