from leones.core.contracts import HardwareProfile, ModelCandidate, TaskRequirements
from leones.router import LeonesRouter


def test_router_selects_local_gguf_backend():
    hardware = HardwareProfile(cpu="Intel i5", ram_gb=16)
    task = TaskRequirements(task_type="coding", required_tools=("filesystem",))
    candidates = [
        ModelCandidate(
            model_id="qwen3-8b",
            quantization="Q4_K_M",
            formats=("GGUF",),
            capabilities=("coding", "filesystem"),
        )
    ]

    decision = LeonesRouter().route(task, hardware, candidates)

    assert decision.model_id == "qwen3-8b"
    assert decision.quantization == "Q4_K_M"
    assert decision.backend == "llama.cpp"
    assert decision.device == "cpu"
