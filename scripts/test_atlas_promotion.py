#!/usr/bin/env python3
"""Small contract tests for the verified-only Atlas promotion boundary."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/atlas_promote_verified.py"
spec = importlib.util.spec_from_file_location("atlas_promote_verified", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_identity_precedence():
    assert (
        mod.canonical_id({"model_id": "Org/Model", "repository_url": "https://x/y"})
        == "Org/Model"
    )


def test_repository_fallback():
    row = {"repository_url": "https://huggingface.co/org/model", "source_url": ""}
    assert mod.canonical_id(row) == "org/model"


def test_unknown_is_not_zero():
    record = mod.build_record(
        {
            "model_id": "org/model",
            "model_name": "org/model",
            "organization": "org",
            "evidence_status": "verified",
            "source_url": "https://huggingface.co/org/model",
        }
    )
    assert record["model_system"]["weight_memory_gb"] is None
    assert record["model_system"]["context_length"] is None


def test_external_evidence_is_not_measurement():
    record = mod.build_record(
        {
            "model_id": "org/model",
            "model_name": "org/model",
            "evidence_status": "verified",
            "source_url": "https://huggingface.co/org/model",
        }
    )
    assert record["evidence"]["evidence_type"] == "external"


if __name__ == "__main__":
    tests = [
        test_identity_precedence,
        test_repository_fallback,
        test_unknown_is_not_zero,
        test_external_evidence_is_not_measurement,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"{len(tests)} promotion contract tests passed")
