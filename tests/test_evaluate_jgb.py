#!/usr/bin/env python3
"""Pruebas del evaluador JGB basado en evidencia.

Fijan dos garantías: la evidencia completa y trazable puede derivar una clase,
y la evidencia incompleta, provisional o sin fuentes no puede fabricar una.
"""
from scripts.evaluate_jgb import evaluate_jgb


def test_complete_evidence_derives_class_from_lowest_dimension():
    evidence = {
        "access": {"level": 5, "status": "verified", "sources": ["a"]},
        "model_control": {"level": 4, "status": "verified", "sources": ["b"]},
        "data_control": {"level": 4, "status": "verified", "sources": ["c"]},
        "autonomy": {"level": 5, "status": "verified", "sources": ["d"]},
        "trust": {"level": 4, "status": "verified", "sources": ["e"]},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] == 4
    assert result["status"] == "supported"
    assert result["unresolved"] == []


def test_missing_dimension_stays_unknown():
    evidence = {
        "access": {"level": 5, "status": "verified", "sources": ["a"]},
        "model_control": {"level": 4, "status": "verified", "sources": ["b"]},
        "data_control": {"level": 4, "status": "verified", "sources": ["c"]},
        "autonomy": {"level": 5, "status": "verified", "sources": ["d"]},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] is None
    assert result["status"] == "unknown"
    assert result["unresolved"] == ["trust"]


def test_provisional_dimension_cannot_derive_verified_class():
    evidence = {
        "access": {"level": 3, "status": "verified", "sources": ["a"]},
        "model_control": {"level": 3, "status": "provisional", "sources": ["b"]},
        "data_control": {"level": 3, "status": "verified", "sources": ["c"]},
        "autonomy": {"level": 3, "status": "verified", "sources": ["d"]},
        "trust": {"level": 3, "status": "verified", "sources": ["e"]},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] is None
    assert result["unresolved"] == ["model_control"]


def test_resolved_dimension_without_source_stays_unknown():
    evidence = {
        "access": {"level": 3, "status": "verified", "sources": []},
        "model_control": {"level": 3, "status": "verified", "sources": ["b"]},
        "data_control": {"level": 3, "status": "verified", "sources": ["c"]},
        "autonomy": {"level": 3, "status": "verified", "sources": ["d"]},
        "trust": {"level": 3, "status": "verified", "sources": ["e"]},
    }
    result = evaluate_jgb(evidence)
    assert result["jgb_class"] is None
    assert result["unresolved"] == ["access"]
