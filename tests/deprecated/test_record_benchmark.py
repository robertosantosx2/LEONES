#!/usr/bin/env python3
"""Historical tests retained with the deprecated benchmark recorder."""

import pytest

from scripts.deprecated.record_benchmark import record_measurement


def sample():
    return {
        "model": "example-model",
        "variant": "Q4_K_M",
        "runtime": "llama.cpp",
        "hardware": "intel-i5-16gb",
        "workload": "chat",
        "quantization": "Q4_K_M",
        "context_tokens": 4096,
        "tokens_per_second": 7.5,
    }


def test_real_measurement_is_marked_measured():
    result = record_measurement(sample(), "2026-08-16T12:00:00+00:00")
    assert result["measurement_type"] == "measured"
    assert result["tokens_per_second"] == 7.5
    assert result["context_tokens"] == 4096
    assert result["measured_at"] == "2026-08-16T12:00:00+00:00"


def test_missing_required_field_is_rejected():
    data = sample()
    del data["runtime"]
    with pytest.raises(ValueError, match="missing required fields"):
        record_measurement(data)


def test_negative_speed_is_rejected():
    data = sample()
    data["tokens_per_second"] = -1
    with pytest.raises(ValueError, match="cannot be negative"):
        record_measurement(data)
