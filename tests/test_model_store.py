from leones.model import ModelInfo
from leones.model_store import ModelStore


def test_model_metadata_roundtrip(tmp_path):
    store = ModelStore(tmp_path / "atlas.sqlite")
    model = ModelInfo(
        model_id="qwen3-8b",
        family="Qwen3",
        format="GGUF",
        quantization="Q4_K_M",
        size_gb=5.0,
        capabilities=("coding",),
        license="Apache-2.0",
    )
    store.add(model)
    assert store.get("qwen3-8b") == model
