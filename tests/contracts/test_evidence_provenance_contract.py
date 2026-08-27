import pytest

from scripts.validate_evidence import validate_evidence


def test_estimated_and_reported_are_not_measured():
    for evidence_type in ("estimated", "reported"):
        evidence = {"evidence_type": evidence_type, "source": "external"}
        assert validate_evidence(evidence)["evidence_type"] == evidence_type


def test_measured_requires_execution_identity_timestamp_and_real_kind():
    with pytest.raises(ValueError, match="execution_id"):
        validate_evidence({"evidence_type": "measured", "measured_at": "2026-08-26T16:00:00Z", "measurement_kind": "real"})
    with pytest.raises(ValueError, match="measured_at"):
        validate_evidence({"evidence_type": "measured", "execution_id": "exec-1", "measurement_kind": "real"})
    with pytest.raises(ValueError, match="measurement_kind=real"):
        validate_evidence({"evidence_type": "measured", "execution_id": "exec-1", "measured_at": "2026-08-26T16:00:00Z"})


def test_synthetic_measurement_can_never_be_promoted_to_measured():
    synthetic = {
        "evidence_type": "measured",
        "source": "internal",
        "execution_id": "synthetic-exec-1",
        "measured_at": "2026-08-26T16:00:00Z",
        "measurement_kind": "synthetic",
        "measured_tps": 42.0,
    }
    with pytest.raises(ValueError, match="synthetic evidence"):
        validate_evidence(synthetic)


def test_synthetic_run_marker_cannot_be_promoted_even_if_kind_is_real():
    synthetic = {
        "evidence_type": "measured",
        "execution_id": "synthetic-exec-2",
        "measured_at": "2026-08-26T16:00:00Z",
        "measurement_kind": "real",
        "run_type": "synthetic",
        "measured_tps": 42.0,
    }
    with pytest.raises(ValueError, match="synthetic evidence"):
        validate_evidence(synthetic)


def test_reported_value_cannot_be_promoted_by_renaming():
    evidence = {"evidence_type": "reported", "source": "external", "measured_tps": 42.0}
    assert validate_evidence(evidence)["evidence_type"] == "reported"
