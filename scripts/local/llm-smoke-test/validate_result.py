#!/usr/bin/env python3
"""Validate a llm-smoke-test v0.1 result without external dependencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SCHEMA_VERSION = "0.1"
REQUIRED = {
    "schema_version",
    "test",
    "timestamp",
    "model",
    "runtime",
    "hardware",
    "configuration",
    "warmup",
    "repetitions",
    "metrics",
    "result",
}
METRICS = {
    "ttft_ms",
    "generation_ms",
    "total_ms",
    "prompt_tokens",
    "generated_tokens",
    "tokens_per_second",
    "peak_ram_bytes",
    "peak_vram_bytes",
}


def validate(payload: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return ["root must be an object"]
    missing = REQUIRED - payload.keys()
    if missing:
        errors.append(f"missing top-level fields: {', '.join(sorted(missing))}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION!r}")
    if not isinstance(payload.get("test"), dict):
        errors.append("test must be an object")
    if not isinstance(payload.get("model"), dict):
        errors.append("model must be an object")
    if not isinstance(payload.get("runtime"), dict):
        errors.append("runtime must be an object")
    if not isinstance(payload.get("hardware"), dict):
        errors.append("hardware must be an object")
    if not isinstance(payload.get("configuration"), dict):
        errors.append("configuration must be an object")
    if not isinstance(payload.get("warmup"), dict):
        errors.append("warmup must be an object")
    if not isinstance(payload.get("metrics"), dict):
        errors.append("metrics must be an object")
    else:
        missing_metrics = METRICS - payload["metrics"].keys()
        if missing_metrics:
            errors.append(
                "missing metrics: " + ", ".join(sorted(missing_metrics))
            )
    if not isinstance(payload.get("result"), dict):
        errors.append("result must be an object")
    elif payload["result"].get("status") not in {"ok", "error", "partial"}:
        errors.append("result.status must be ok, error or partial")
    repetitions = payload.get("repetitions")
    if not isinstance(repetitions, int) or repetitions < 1:
        errors.append("repetitions must be an integer >= 1")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LEONES smoke-test JSON")
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.result.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 1
    errors = validate(payload)
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"VALID: schema {SCHEMA_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
