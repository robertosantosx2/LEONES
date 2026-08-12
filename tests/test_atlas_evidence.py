import pytest

from leones.atlas_evidence import Evidence, validate_for_atlas


def test_evidence_requires_explicit_reviewer():
    item = Evidence("https://example.org", "reported", "benchmark")
    assert validate_for_atlas(item, "Roberto").status == "atlas-evidence"


def test_evidence_cannot_be_promoted_without_reviewer():
    item = Evidence("https://example.org", "reported", "benchmark")
    with pytest.raises(ValueError):
        validate_for_atlas(item, "")


def test_evidence_cannot_be_promoted_twice():
    item = Evidence("https://example.org", "reported", "benchmark", "atlas-evidence")
    with pytest.raises(ValueError):
        validate_for_atlas(item, "Roberto")
