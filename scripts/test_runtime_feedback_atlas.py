import csv
import json
from pathlib import Path

from scripts.runtime_feedback_atlas import apply_feedback, load_feedback


def test_measured_feedback_replaces_performance_and_preserves_provenance():
    rows = [{"model_id": "demo/model", "tokens_per_second": "3"}]
    feedback = {
        "demo/model": {
            "model_id": "demo/model",
            "evidence_type": "measured",
            "execution_id": "exec-42",
            "metrics": {"measured_tps": 12.5},
            "provenance": {"source": "FreeToken", "measured_at": "2026-08-24T00:00:00Z"},
        }
    }
    out = apply_feedback(rows, feedback)[0]
    assert out["tokens_per_second"] == "12.5"
    assert out["performance_evidence_type"] == "measured"
    assert out["performance_evidence_id"] == "exec-42"
    assert out["performance_evidence_source"] == "FreeToken"


def test_reported_feedback_does_not_overwrite_measurement():
    rows = [{"model_id": "demo/model", "tokens_per_second": "12.5", "performance_evidence_type": "measured"}]
    feedback = {"demo/model": {"model_id": "demo/model", "evidence_type": "reported", "metrics": {"measured_tps": 99}}}
    out = apply_feedback(rows, feedback)[0]
    assert out["tokens_per_second"] == "12.5"
    assert out["performance_evidence_type"] == "measured"


def test_jsonl_loader_uses_latest_record(tmp_path: Path):
    path = tmp_path / "feedback.jsonl"
    path.write_text("\n".join([
        json.dumps({"model_id": "m", "evidence_type": "measured", "metrics": {"measured_tps": 1}}),
        json.dumps({"model_id": "m", "evidence_type": "measured", "metrics": {"measured_tps": 2}}),
    ]) + "\n", encoding="utf-8")
    assert load_feedback(path)["m"]["metrics"]["measured_tps"] == 2
