from pathlib import Path

from leones.core.contracts import ModelCandidate, RouteDecision
from leones.runtime_manager import LocalModelSource


def test_local_model_source_resolves_gguf(tmp_path: Path):
    model_path = tmp_path / "qwen3-8b.gguf"
    model_path.write_bytes(b"test")
    source = LocalModelSource(tmp_path)
    model = ModelCandidate(model_id="qwen3-8b", formats=("GGUF",))
    assert source.resolve(model) == model_path


def test_route_decision_can_carry_model_path():
    decision = RouteDecision(
        model_id="qwen3-8b",
        quantization="Q4_K_M",
        backend="llama.cpp",
        device="cpu",
        parameters={"model_path": "/models/qwen3-8b.gguf"},
    )
    assert decision.parameters["model_path"].endswith(".gguf")
