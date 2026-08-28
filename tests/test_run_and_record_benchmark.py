#!/usr/bin/env python3
"""Tests for the active benchmark execution recorder."""

import pytest

from scripts.run_and_record_benchmark import run_and_record


def metadata():
    return {
        "model": "example-model",
        "variant": "Q4_K_M",
        "runtime": "fake-runtime",
        "hardware": "test-machine",
        "workload": "chat",
        "quantization": "Q4_K_M",
        "context_tokens": 4096,
    }


def test_runner_extracts_measurement_from_runtime_output():
    result = run_and_record(
        ["python", "-c", "print('generation: 7.5 tok/s')"],
        metadata(),
        r"([0-9]+(?:\.[0-9]+)?)\s*tok/s",
    )
    assert result["tokens_per_second"] == 7.5
    assert result["measurement_type"] == "measured"


def test_runner_rejects_missing_measurement():
    with pytest.raises(ValueError, match="does not contain"):
        run_and_record(
            ["python", "-c", "print('generation complete')"],
            metadata(),
            r"([0-9]+(?:\.[0-9]+)?)\s*tok/s",
        )


def test_runner_rejects_failed_command():
    with pytest.raises(RuntimeError, match="failed with exit code"):
        run_and_record(
            ["python", "-c", "raise SystemExit(3)"],
            metadata(),
            r"([0-9]+(?:\.[0-9]+)?)\s*tok/s",
        )
