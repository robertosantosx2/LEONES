#!/usr/bin/env python3
"""Pruebas de la unión entre medición real y CABE/RULA."""

import pytest

from scripts.enrich_measured_performance import enrich_measured_performance


def measurement(value):
    return {
        "model": "example",
        "runtime": "llama.cpp",
        "hardware": "test-host",
        "tokens_per_second": value,
        "measurement_type": "measured",
    }


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0.5, "NO_CABE"), (1, "CABE"), (9.99, "CABE"), (10, "RULA"), (100, "RULA"), (100.01, "RULA+")],
)
def test_real_measurement_gets_correct_class_without_changing_speed(value, expected):
    result = enrich_measured_performance(measurement(value))
    assert result["tokens_per_second"] == value
    assert result["performance_class"] == expected
    assert result["measurement_type"] == "measured"


def test_estimated_measurement_is_rejected():
    data = measurement(7)
    data["measurement_type"] = "estimated"
    with pytest.raises(ValueError, match="real measurement"):
        enrich_measured_performance(data)
