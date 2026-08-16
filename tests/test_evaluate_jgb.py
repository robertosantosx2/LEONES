#!/usr/bin/env python3
"""Pruebas del evaluador JGB basado en evidencia.

Estas pruebas fijan dos garantías sencillas: con evidencia completa se puede
derivar una clase, y con evidencia incompleta el sistema debe conservar
``unknown`` en vez de inventar una clasificación.
"""
from scripts.evaluate_jgb import evaluate_jgb


def test_complete_evidence_derives_class_from_lowest_dimension():
    evidence = {
        "access": {"level": 5, "sources": ["a"]},
        "model_control": {"level": 4, "sources": ["b"]},
        "data_control": {"level": 4, "sources": ["c"]},
        "autonomy": {"level": 5, "sources": ["d"]},
        "trust": {"level": 4, "sources": ["e"]},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] == 4
    assert result["status"] == "supported"
    assert result["unresolved"] == []


def test_missing_dimension_stays_unknown():
    evidence = {
        "access": {"level": 5},
        "model_control": {"level": 4},
        "data_control": {"level": 4},
        "autonomy": {"level": 5},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] is None
    assert result["status"] == "unknown"
    assert result["unresolved"] == ["trust"]
