from leones.atlas_store import SQLiteAtlas
from leones.core.contracts import HardwareProfile, ModelCandidate


def test_sqlite_atlas_roundtrip(tmp_path):
    atlas = SQLiteAtlas(tmp_path / "atlas.sqlite")
    model = ModelCandidate(
        model_id="qwen3-8b",
        quantization="Q4_K_M",
        formats=("GGUF",),
        capabilities=("coding",),
    )
    atlas.add_model(model)

    candidates = atlas.candidates(HardwareProfile(cpu="i5", ram_gb=16))
    assert candidates == [model]
