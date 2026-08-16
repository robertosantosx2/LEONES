#!/usr/bin/env python3
"""Pruebas del publicador de evidencia medida."""

import json

import pytest

from scripts.publish_measured_benchmark import publish


def measurement(value=7.5):
    return {
        "model": "m1",
        "hardware": "h1",
        "runtime": "llama.cpp",
        "tokens_per_second": value,
        "measurement_type": "measured",
    }


def test_publish_writes_one_validated_jsonl_record(tmp_path):
    path = tmp_path / "evidence" / "benchmarks.jsonl"
    result = publish(path, measurement())
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    stored = json.loads(lines[0])
    assert stored["tokens_per_second"] == 7.5
    assert stored["performance_class"] == "CABE"
    assert result == stored


def test_publish_rejects_estimated_record(tmp_path):
    data = measurement()
    data["measurement_type"] = "estimated"
    with pytest.raises(ValueError, match="only measured"):
        publish(tmp_path / "benchmarks.jsonl", data)
