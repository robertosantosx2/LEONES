from scripts.integrations.ods_adapter import ODSAdapter
from scripts.integrations.magnitude_adapter import MagnitudeAdapter


def test_ods_reports_fixed_ref_as_evidence():
    result = ODSAdapter("v2.6.0").evidence()
    assert result.state == "REPORTED"
    assert result.product == "ODS"
    assert result.version == "v2.6.0"
    assert result.source == "fixed_ref"


def test_magnitude_reports_fixed_ref_as_evidence():
    result = MagnitudeAdapter("fixed-ref").evidence()
    assert result.state == "REPORTED"
    assert result.product == "Magnitude"
    assert result.version == "fixed-ref"
    assert result.source == "fixed_ref"
