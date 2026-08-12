from leones.atlas import AtlasRecord, InMemoryAtlas
from leones.core.contracts import HardwareProfile, ModelCandidate
from leones.engine import LeonesEngine


def test_engine_connects_task_atlas_and_router():
    atlas = InMemoryAtlas([
        AtlasRecord(ModelCandidate(
            model_id="qwen3-8b",
            quantization="Q4_K_M",
            formats=("GGUF",),
            capabilities=("coding", "filesystem", "shell"),
        ))
    ])
    hardware = HardwareProfile(cpu="Intel i5", ram_gb=16)

    decision = LeonesEngine(atlas).decide(
        "corrige el código Python y ejecuta los tests", hardware
    )

    assert decision.task_type == "coding"
    assert decision.route.model_id == "qwen3-8b"
    assert decision.route.backend == "llama.cpp"
