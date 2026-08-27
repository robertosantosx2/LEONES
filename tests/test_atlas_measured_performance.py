#!/usr/bin/env python3
"""Pruebas de integración de mediciones reales en Atlas."""

from scripts.atlas_measured_performance import integrate_measurements


def test_measured_result_is_added_to_matching_hardware_and_runtime():
    rows = [{"model_id": "m1", "hardware": "h1", "runtime": "llama.cpp"}]
    measurements = [{
        "model_id": "m1", "hardware": "h1", "runtime": "llama.cpp",
        "tokens_per_second": 7.5, "measurement_type": "measured",
        "evidence_type": "measured", "execution_id": "run-1",
        "measured_at": "2026-08-16T12:00:00+00:00", "measurement_kind": "real",
    }]
    result = integrate_measurements(rows, measurements)
    assert result[0]["measured_tokens_per_second"] == 7.5
    assert result[0]["measured_performance_class"] == "CABE"
    assert result[0]["measurement_type"] == "measured"
    assert result[0]["execution_id"] == "run-1"


def test_estimated_measurement_is_not_integrated():
    rows = [{"model_id": "m1", "hardware": "h1", "runtime": "llama.cpp"}]
    measurements = [{
        "model_id": "m1", "hardware": "h1", "runtime": "llama.cpp",
        "tokens_per_second": 7.5, "measurement_type": "estimated",
    }]
    result = integrate_measurements(rows, measurements)
    assert "measured_tokens_per_second" not in result[0]


def test_non_matching_hardware_is_not_integrated():
    rows = [{"model_id": "m1", "hardware": "h2", "runtime": "llama.cpp"}]
    measurements = [{
        "model_id": "m1", "hardware": "h1", "runtime": "llama.cpp",
        "tokens_per_second": 7.5, "measurement_type": "measured",
        "evidence_type": "measured", "execution_id": "run-2",
        "measured_at": "2026-08-16T12:00:00+00:00", "measurement_kind": "real",
    }]
    result = integrate_measurements(rows, measurements)
    assert "measured_tokens_per_second" not in result[0]
