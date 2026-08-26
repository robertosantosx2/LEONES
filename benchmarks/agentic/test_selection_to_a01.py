#!/usr/bin/env python3
"""Deterministic integration test for selector -> runtime-selection.v1 -> A01.

This is intentionally not a model benchmark. The trusted runtime command is a
small deterministic fixture that emits the canonical A01 tool calls. The test
proves the wiring and evidence contract without requiring local model software
or hardware.
"""
from __future__ import annotations

import sys
from pathlib import Path

from scripts.run_a01_selected import run_selected


def test_selector_to_a01_measured_evidence(tmp_path: Path) -> None:
    runtime_code = (
        "import sys; "
        "print('{\"tool\":\"lookup_model\",\"arguments\":{\"model_id\":\"demo-2\"}}'); "
        "print('{\"tool\":\"write_report\",\"arguments\":{\"path\":\"report.txt\"}}')"
    )
    selection = {
        "schema_version": "1.0",
        "candidates": [
            {
                "model_id": "demo-2",
                "model_name": "Beta",
                "runtime": "fixture-runtime",
                "runtime_version": "test-1",
                "quantization": "fixture",
                "optimization_families": [],
                "selection_status": "TOP_N",
                "rank": 1,
                "fit_score": 1.0,
                "evidence_level": "estimated",
                "llmfit": {"estimated_tps": 10.0},
            }
        ],
    }

    result = run_selected(
        selection,
        runtime_commands={"fixture-runtime": [sys.executable, "-c", runtime_code]},
        workspace=tmp_path,
        prompt="Execute A01",
    )

    assert result["agentic"]["task_id"] == "A01"
    assert result["agentic"]["outcome"]["status"] == "success"
    assert result["agentic"]["outcome"]["score"] == 1.0
    assert result["agentic"]["grader"]["id"] == "A01-grader"
    assert result["agentic"]["grader"]["version"] == "1.0"
    assert result["agentic"]["metrics"]["tool_calls"] == 2
    assert result["agentic"]["metrics"]["runtime_wall_seconds"] >= 0
    assert result["evidence"]["evidence_type"] == "measured"
    assert result["evidence"]["execution_id"] == result["agentic"]["execution_id"]
    assert result["evidence"]["measured_at"]
    assert result["runtime_selection"]["execution_plans"][0]["execution_authorized"] is True
    assert (tmp_path / "report.txt").read_text(encoding="utf-8") == "Model: Beta\n"


def test_runtime_gate_blocks_untrusted_selection() -> None:
    from scripts.runtime_gate import gate_selection

    selection = {
        "candidates": [
            {
                "model_id": "demo-2",
                "model_name": "Beta",
                "runtime": "missing-runtime",
                "quantization": "fixture",
                "optimization_families": [],
                "selection_status": "TOP_N",
            }
        ]
    }
    result = gate_selection(selection, runtime_commands={})
    assert result["counts"] == {"plans": 1, "blocked": 0}
    assert result["execution_plans"][0]["execution_authorized"] is False
    assert result["execution_plans"][0]["runtime"]["command"] is None
