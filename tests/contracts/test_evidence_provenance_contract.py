import pytest

from scripts.validate_evidence import validate_evidence


def test_estimated_and_reported_are_not_measured():
    for evidence_type in ("estimated", "reported"):
        evidence = {"evidence_type": evidence_type, "source": "external"}
        assert validate_evidence(evidence)["evidence_type"] == evidence_type


def test_measured_requires_execution_identity_and_timestamp():
    with pytest.raises(ValueError, match="execution_id"):
        validate_evidence({"evidence_type": "measured", "measured_at": "2026-08-26T16:00:00Z"})
    with pytest.raises(ValueError, match="measured_at"):
        validate_evidence({"evidence_type": "measured", "execution_id": "exec-1"})


def test_reported_value_cannot_be_promoted_by_renaming():
    evidence = {"evidence_type": "reported", "source": "external", "measured_tps": 42.0}
    assert validate_evidence(evidence)["evidence_type"] == "reported"
