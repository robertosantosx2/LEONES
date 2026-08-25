from scripts.prediction_error import compare_estimators, error_metrics


def test_error_metrics():
    result = error_metrics(12.0, 10.0)
    assert result == {"abs": 2.0, "pct": 20.0, "bias": 2.0, "factor": 1.2}


def test_missing_measurement_does_not_create_fake_error():
    result = compare_estimators(llmfit=12.0, canirun=10.0, measured=None)
    assert result["measured_tps"] is None
    assert result["llmfit"]["error"]["abs"] is None
    assert result["canirun"]["error"]["pct"] is None


def test_comparison_keeps_measurement_independent():
    result = compare_estimators(llmfit=12.0, canirun=10.0, measured=11.0)
    assert result["measured_tps"] == 11.0
    assert result["llmfit"]["estimated_tps"] == 12.0
    assert result["canirun"]["estimated_tps"] == 10.0
