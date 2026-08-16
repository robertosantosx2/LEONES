#!/usr/bin/env python3
"""Pruebas del filtro de promoción de evidencia empírica."""

import pytest

from scripts.validate_measured_benchmark import validate_measured_benchmark


def valid():
    return {
        "model": "m1",
        "hardware": "h1",
        "runtime": "llama.cpp",
        "tokens_per_second": 8.2,
        "measurement_type": "measured",
    }


def test_valid_measured_benchmark_is_preserved():
    result = validate_measured_benchmark(valid())
    assert result["measurement_type"] == "measured"
    assert result["tokens_per_second"] == 8.2


@pytest.mark.parametrize("field", ["model", "hardware", "runtime"])
def test_missing_identity_is_rejected(field):
    data = valid()
    del data[field]
    with pytest.raises(ValueError, match="identity fields"):
        validate_measured_benchmark(data)


def test_estimated_benchmark_is_rejected():
    data = valid()
    data["measurement_type"] = "estimated"
    with pytest.raises(ValueError, match="only measured"):
        validate_measured_benchmark(data)
