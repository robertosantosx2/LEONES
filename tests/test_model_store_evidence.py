from leones.atlas_evidence import Evidence
from leones.model import ModelInfo
from leones.model_store import ModelStore


def test_store_persists_external_evidence(tmp_path):
    store = ModelStore(tmp_path / "atlas.sqlite")
    store.add(ModelInfo("model-a"))
    item = Evidence("https://example.org", "reported", "benchmark")
    store.add_evidence("model-a", item)
    assert store.evidence("model-a") == [item]


def test_store_keeps_review_state(tmp_path):
    store = ModelStore(tmp_path / "atlas.sqlite")
    store.add(ModelInfo("model-a"))
    item = Evidence("https://example.org", "measured", "benchmark", "atlas-evidence")
    store.add_evidence("model-a", item, reviewer="reviewer", reviewed_at="2026-08-12")
    assert store.evidence("model-a")[0].status == "atlas-evidence"
