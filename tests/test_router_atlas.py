from leones.model import ModelInfo
from leones.model_store import ModelStore
from leones.router_atlas import candidates_from_atlas


def test_router_reads_candidates_from_atlas(tmp_path):
    path = tmp_path / "atlas.sqlite"
    store = ModelStore(path)
    store.add(ModelInfo("coder", capabilities=("coding",), source="model.gguf"))
    candidates = candidates_from_atlas(path)
    assert len(candidates) == 1
    assert candidates[0].model_id == "coder"
    assert "coding" in candidates[0].capabilities
