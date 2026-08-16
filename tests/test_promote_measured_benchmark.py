#!/usr/bin/env python3
"""Pruebas del paso de promoción a Atlas."""

import pytest

from scripts.promote_measured_benchmark import promote


def measurement(value=7.5):
    return {
        "model": "m1",
        "hardware": "h1",
        "runtime": "llama.cpp",
        "tokens_per_second": value,
        "measurement_type": "measured",
    }


def test_promote_validates_and_adds_performance_class():
    result = promote(measurement())
    assert result["measurement_type"] == "measured"
    assert result["tokens_per_second"] == 7.5
    assert result["performance_class"] == "CABE"


def test_promote_rejects_estimates():
    data = measurement()
    data["measurement_type"] = "estimated"
    with pytest.raises(ValueError, match="only measured"):
        promote(data)
