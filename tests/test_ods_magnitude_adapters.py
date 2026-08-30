from scripts.integrations.ods_adapter import ODSAdapter
from scripts.integrations.magnitude_adapter import MagnitudeAdapter


def test_ods_preflight_is_safe_and_fixed():
    result = ODSAdapter(expected_ref="v2.6.0").preflight()
    assert result.status == "PASS"
    assert result.checks["expected_ref"] == "v2.6.0"
    assert result.checks["install"] == "not_run"


def test_magnitude_preflight_is_safe_and_fixed():
    result = MagnitudeAdapter(expected_ref="fixed-ref").preflight()
    assert result.status == "PASS"
    assert result.checks["expected_ref"] == "fixed-ref"
    assert result.checks["install"] == "not_run"
