from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate_recommendation_gate.py"


def run_gate(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "decision.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(VALIDATOR), str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def base_decision() -> dict:
    return {
        "entity": "demo/model",
        "evidence_profile": {"source": "JALON5", "status": "provisional"},
        "decision": "verify_first",
        "rationale": "external fit is available but physical evidence is missing",
        "unknowns": ["local throughput"],
        "next_action": "measure",
        "external_scores_used": True,
        "minimum_evidence_met": False,
    }


def test_provisional_external_decision_routes_to_measure(tmp_path: Path) -> None:
    result = run_gate(tmp_path, base_decision())
    assert result.returncode == 0, result.stderr


def test_recommend_requires_minimum_evidence(tmp_path: Path) -> None:
    payload = base_decision()
    payload.update({"decision": "recommend", "next_action": "recommend", "minimum_evidence_met": False})
    result = run_gate(tmp_path, payload)
    assert result.returncode != 0
    assert "minimum_evidence_met" in result.stderr


def test_recommend_is_valid_only_with_evidence(tmp_path: Path) -> None:
    payload = base_decision()
    payload.update({"decision": "recommend", "next_action": "recommend", "minimum_evidence_met": True})
    result = run_gate(tmp_path, payload)
    assert result.returncode == 0, result.stderr


def test_external_score_requires_nonempty_evidence_profile(tmp_path: Path) -> None:
    payload = base_decision()
    payload["evidence_profile"] = {}
    result = run_gate(tmp_path, payload)
    assert result.returncode != 0
    assert "evidence profile" in result.stderr

    payload.pop("evidence_profile")
    result = run_gate(tmp_path, payload)
    assert result.returncode != 0
    assert "missing required field: evidence_profile" in result.stderr
