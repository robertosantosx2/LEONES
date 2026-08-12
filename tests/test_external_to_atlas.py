from leones.external_to_atlas import ExternalEstimate, prepare_for_review


def test_external_estimate_stays_unvalidated():
    item = ExternalEstimate("model-a", "tokens_s", "18", "https://example.org")
    record = prepare_for_review(item)
    assert record["status"] == "external-unvalidated"
    assert record["source"] == "https://example.org"
