#!/usr/bin/env python3
"""Dependency-free tests for the v0.1 result validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validate_result.py"


def valid_result() -> dict:
    return {
        "schema_version": "0.1",
        "test": {"name": "llm-smoke-test", "mode": "experimental"},
        "timestamp": "2026-08-16T00:00:00+00:00",
        "model": {"id": "model.gguf"},
        "runtime": {"name": "llama.cpp", "adapter": "llama-cpp"},
        "hardware": {"os": "Linux", "architecture": "x86_64"},
        "configuration": {"requested_new_tokens": 32},
        "warmup": {"enabled": False, "runs": 0},
        "repetitions": 1,
        "metrics": {
            "ttft_ms": None,
            "generation_ms": None,
            "total_ms": 100.0,
            "prompt_tokens": None,
            "generated_tokens": None,
            "tokens_per_second": None,
            "peak_ram_bytes": None,
            "peak_vram_bytes": None,
        },
        "result": {"status": "ok", "error": None},
    }


def run(payload: dict) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "result.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )


def assert_valid() -> None:
    completed = run(valid_result())
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "VALID" in completed.stdout


def assert_invalid_missing_metric() -> None:
    payload = valid_result()
    del payload["metrics"]["tokens_per_second"]
    completed = run(payload)
    assert completed.returncode != 0
    assert "missing metrics" in completed.stdout


def assert_invalid_schema_version() -> None:
    payload = valid_result()
    payload["schema_version"] = "9.9"
    completed = run(payload)
    assert completed.returncode != 0
    assert "schema_version" in completed.stdout


def assert_invalid_repetitions() -> None:
    payload = valid_result()
    payload["repetitions"] = 0
    completed = run(payload)
    assert completed.returncode != 0
    assert "repetitions" in completed.stdout


def assert_invalid_json() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
    assert completed.returncode != 0
    assert "INVALID" in completed.stdout


def main() -> int:
    tests = [
        assert_valid,
        assert_invalid_missing_metric,
        assert_invalid_schema_version,
        assert_invalid_repetitions,
        assert_invalid_json,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
