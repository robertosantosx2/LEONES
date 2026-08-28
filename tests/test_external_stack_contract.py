from scripts.integrations.external_stack import (
    BenchmarkResult,
    EvidenceResult,
    HealthResult,
    PreflightResult,
    merge_evidence,
)

def test_contracts_have_expected_states():
    assert PreflightResult("PASS", "linux", "x86_64").status == "PASS"
    assert HealthResult("HEALTHY").status == "HEALTHY"
    assert EvidenceResult("REPORTED", "ODS").state == "REPORTED"
    assert BenchmarkResult("MEASURED", tokens_per_second=1.0).state == "MEASURED"

def test_merge_evidence_does_not_create_measured_data():
    evidence = EvidenceResult("REPORTED", "ODS", model="test-model")
    out = merge_evidence({}, evidence)

    assert out["state"] == "REPORTED"
    assert out["product"] == "ODS"
    assert out["model"] == "test-model"
    assert "tokens_per_second" not in out
