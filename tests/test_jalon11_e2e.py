from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/jalon11_e2e.py"


def base_operation() -> dict:
    return {
        "schema": "leones-e2e-operation.v1",
        "operation_id": "op-12345678",
        "selection_ref": "selection-1",
        "runtime_ref": "runtime-llama-cpp",
        "execution_ref": "execution-1",
        "measurement_ref": "measurement-1",
        "evidence_refs": ["evidence-1"],
        "decision_ref": "decision-1",
        "recommendation_ref": "recommendation-1",
        "publication_ref": "publication-1",
        "output_ref": "output-1",
        "trace_ref": "trace-1",
        "status": "published",
    }


def run_gate(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    src = tmp_path / "operation.json"
    dst = tmp_path / "output.json"
    src.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(src), str(dst)], text=True, capture_output=True)


def test_valid_operation_round_trips(tmp_path: Path) -> None:
    payload = base_operation()
    result = run_gate(tmp_path, payload)
    assert result.returncode == 0, result.stderr
    assert json.loads((tmp_path / "output.json").read_text()) == payload


def test_missing_stage_reference_is_rejected(tmp_path: Path) -> None:
    payload = base_operation()
    payload["recommendation_ref"] = ""
    result = run_gate(tmp_path, payload)
    assert result.returncode == 1
    assert "recommendation_ref" in result.stderr


def test_parallel_scoring_is_rejected(tmp_path: Path) -> None:
    payload = base_operation()
    payload["score"] = 0.9
    result = run_gate(tmp_path, payload)
    assert result.returncode == 1
    assert "parallel scoring" in result.stderr


def test_unknown_status_is_rejected(tmp_path: Path) -> None:
    payload = base_operation()
    payload["status"] = "recommended_and_scored"
    result = run_gate(tmp_path, payload)
    assert result.returncode == 1
    assert "invalid status" in result.stderr
