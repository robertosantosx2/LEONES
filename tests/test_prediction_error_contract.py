import json
from pathlib import Path


def test_prediction_error_fixture_keeps_estimates_separate_from_measurement():
    path = Path("tests/fixtures/prediction_error/sample.json")
    row = json.loads(path.read_text(encoding="utf-8"))
    measured = row["measured_tps"]
    assert measured > 0
    for source in ("llmfit", "canirun"):
        prediction = row[source]["estimated_tps"]
        assert prediction is not None
        assert row["errors"][f"{source}_abs"] == abs(prediction - measured)
        assert abs(row["errors"][f"{source}_pct"] - abs(prediction - measured) / measured * 100) < 1e-9


def test_prediction_error_has_required_identity_fields():
    row = json.loads(Path("tests/fixtures/prediction_error/sample.json").read_text(encoding="utf-8"))
    for field in ("model_id", "quantization", "runtime", "hardware_profile_id", "context_tokens"):
        assert row[field]
