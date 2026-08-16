#!/usr/bin/env python3
"""Dependency-free tests for the llama.cpp adapter's pure functions."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ADAPTER = Path(__file__).resolve().parents[1] / "adapters" / "llama-cpp" / "run.py"
spec = importlib.util.spec_from_file_location("llama_adapter", ADAPTER)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


def test_parse_timing_known_fields() -> None:
    text = """
    prompt eval tokens: 128
    generated tokens: 32
    generation time: 1600 ms
    tokens/s: 20.0
    ttft: 250 ms
    """
    timing = module.parse_timing(text, "")
    assert timing["prompt_tokens"] == 128
    assert timing["generated_tokens"] == 32
    assert timing["generation_ms"] == 1600.0
    assert timing["tokens_per_second"] == 20.0
    assert timing["ttft_ms"] == 250.0


def test_parse_timing_unknown_fields_are_null() -> None:
    timing = module.parse_timing("ordinary runtime output", "")
    assert all(value is None for value in timing.values())


def test_validate_result_accepts_minimal_valid_payload() -> None:
    payload = {
        "schema_version": "0.1",
        "test": {},
        "timestamp": "2026-08-16T00:00:00+00:00",
        "model": {},
        "runtime": {},
        "hardware": {},
        "configuration": {},
        "warmup": {},
        "repetitions": 1,
        "metrics": {
            "ttft_ms": None,
            "generation_ms": None,
            "total_ms": 1.0,
            "prompt_tokens": None,
            "generated_tokens": None,
            "tokens_per_second": None,
            "peak_ram_bytes": None,
            "peak_vram_bytes": None,
        },
        "result": {"status": "ok", "error": None},
    }
    assert module.validate_result(payload) == []


def test_validate_result_rejects_missing_metric() -> None:
    payload = {"schema_version": "0.1", "metrics": {}}
    errors = module.validate_result(payload)
    assert errors
    assert any("missing top-level fields" in error for error in errors)
    assert any("missing metrics" in error for error in errors)


def main() -> int:
    tests = [
        test_parse_timing_known_fields,
        test_parse_timing_unknown_fields_are_null,
        test_validate_result_accepts_minimal_valid_payload,
        test_validate_result_rejects_missing_metric,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
