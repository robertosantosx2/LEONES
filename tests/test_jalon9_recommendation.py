from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "jalon9_recommend.py"


def base() -> dict:
    return {
        "schema": "leones-recommendation.v1",
        "recommendation_id": "rec-000001",
        "entity": "Qwen3-0.6B",
        "decision_ref": "artifacts/decision.json",
        "evidence_refs": ["artifacts/runtime-benchmark-evidence.json"],
        "status": "recommend",
        "rationale": "Decision is supported by validated measured evidence.",
        "unknowns": [],
        "next_action": "recommend",
        "minimum_evidence_met": True,
    }


def run(tmp_path: Path, payload: dict) -> subprocess.CompletedProcess[str]:
    path = tmp_path / "recommendation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], text=True, capture_output=True)


def test_valid_recommendation(tmp_path: Path) -> None:
    result = run(tmp_path, base())
    assert result.returncode == 0, result.stderr


def test_recommendation_requires_evidence(tmp_path: Path) -> None:
    payload = base()
    payload["evidence_refs"] = []
    result = run(tmp_path, payload)
    assert result.returncode != 0


def test_verify_first_preserves_unknowns(tmp_path: Path) -> None:
    payload = base()
    payload.update(status="verify_first", next_action="verify", unknowns=["runtime version not verified"])
    result = run(tmp_path, payload)
    assert result.returncode == 0, result.stderr


def test_reject_has_explicit_action(tmp_path: Path) -> None:
    payload = base()
    payload.update(status="reject", next_action="reject", rationale="Decision gate rejected the candidate.")
    result = run(tmp_path, payload)
    assert result.returncode == 0, result.stderr


def test_parallel_scoring_is_forbidden(tmp_path: Path) -> None:
    payload = base()
    payload["score"] = 0.91
    result = run(tmp_path, payload)
    assert result.returncode != 0
