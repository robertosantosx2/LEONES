from scripts.validate_evidence import promote_to_verified, validate_evidence


def test_estimated_and_reported_are_not_measurements():
    assert validate_evidence({"evidence_type": "estimated"})["evidence_type"] == "estimated"
    assert validate_evidence({"evidence_type": "reported"})["evidence_type"] == "reported"


def test_measured_requires_execution_identity():
    try:
        validate_evidence({"evidence_type": "measured"})
    except ValueError as exc:
        assert "execution_id" in str(exc)
    else:
        raise AssertionError("measured evidence without execution_id was accepted")


def test_measured_can_be_explicitly_verified():
    measured = {"evidence_type": "measured", "execution_id": "run-1", "measured_at": "2026-08-21T00:00:00+00:00"}
    verified = promote_to_verified(
        measured,
        verifier="test-verifier",
        method="repeat-and-compare",
        verified_at="2026-08-21T00:01:00+00:00",
    )
    assert verified["evidence_type"] == "verified"
