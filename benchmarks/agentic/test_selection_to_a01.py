#!/usr/bin/env python3
"""Deterministic integration tests for the canonical V1 execution path."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from scripts.run_a01_selected import run_selected


def _selection() -> dict:
    return {
        "schema_version": "1.0",
        "candidates": [
            {
                "model_id": "demo-2",
                "model_name": "Beta",
                "runtime": "llama.cpp",
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


def _runtime_code() -> str:
    return (
        "import sys; "
        "print('{\"tool\":\"lookup_model\",\"arguments\":{\"model_id\":\"demo-2\"}}'); "
        "print('{\"tool\":\"write_report\",\"arguments\":{\"path\":\"report.txt\"}}')"
    )


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def test_selector_to_a01_measured_evidence(tmp_path: Path) -> None:
    result = run_selected(
        _selection(),
        runtime_commands={"llama.cpp": [sys.executable, "-c", _runtime_code()]},
        workspace=tmp_path,
        prompt="Execute A01",
    )

    assert result["agentic"]["task_id"] == "A01"
    assert result["agentic"]["outcome"]["status"] == "success"
    assert result["agentic"]["outcome"]["score"] == 1.0
    assert result["agentic"]["grader"]["id"] == "A01-grader"
    assert result["agentic"]["grader"]["version"] == "1.1"
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
    assert result["counts"] == {"plans": 0, "blocked": 1}
    assert result["blocked"][0]["reason"] == "unknown runtime: missing-runtime"


def test_direct_a01_selector_cli_without_pythonpath(tmp_path: Path) -> None:
    """The selector CLI itself must work from a clean Debian/CI shell."""
    root = Path(__file__).resolve().parents[2]
    selection_file = tmp_path / "selection.json"
    commands_file = tmp_path / "runtime-commands.json"
    output_file = tmp_path / "executor-result.json"
    workspace = tmp_path / "workspace"
    selection_file.write_text(json.dumps(_selection()), encoding="utf-8")
    commands_file.write_text(
        json.dumps({"llama.cpp": [sys.executable, "-c", _runtime_code()]}),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/run_a01_selected.py",
            "--selection",
            str(selection_file),
            "--runtime-commands",
            str(commands_file),
            "--workspace",
            str(workspace),
            "--out",
            str(output_file),
        ],
        cwd=root,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["agentic"]["outcome"]["status"] == "success"
    assert payload["agentic"]["grader"]["status"] == "passed"
    assert (workspace / "report.txt").read_text(encoding="utf-8") == "Model: Beta\n"


def test_canonical_a01_benchmark_without_pythonpath(tmp_path: Path) -> None:
    """Prove the canonical A01 benchmark path from a clean environment."""
    root = Path(__file__).resolve().parents[2]
    selection_file = tmp_path / "selection.json"
    commands_file = tmp_path / "runtime-commands.json"
    output_file = tmp_path / "runtime-benchmark.json"
    selection_file.write_text(json.dumps(_selection()), encoding="utf-8")
    commands_file.write_text(
        json.dumps({"llama.cpp": [sys.executable, "-c", _runtime_code()]}),
        encoding="utf-8",
    )

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/a01_runtime_benchmark.py",
            "--selection",
            str(selection_file),
            "--runtime-commands",
            str(commands_file),
            "--workspace",
            str(tmp_path / "workspace"),
            "--out",
            str(output_file),
        ],
        cwd=root,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr

    payload = json.loads(output_file.read_text(encoding="utf-8"))
    benchmark = payload["evidence"]["runtime_benchmark"]

    assert payload["evidence"]["schema"] == "evidence.v1"
    assert benchmark["schema"] == "runtime-benchmark.v1"
    assert benchmark["status"] == "measured"
    assert benchmark["task"] == "A01"
    assert benchmark["grader_pass"] is True
    assert benchmark["runtime"] == "llama.cpp"
    assert benchmark["model"] == "demo-2"
    assert benchmark["executor_result_sha256"]
