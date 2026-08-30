from scripts.model_selector import select
from scripts.runtime_gate import resolve_runtime


MODEL_PATH = "artifacts/models/Qwen3-0.6B-Q4_K_M.gguf"
MODEL_SHA256 = "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"


def test_selection_to_llama_cpp_plan_preserves_runtime_format_and_artifact():
    rows = [{
        "model_id": "Qwen3-0.6B-Q4_K_M",
        "model_name": "Qwen3-0.6B-Q4_K_M",
        "runtime": "llama.cpp",
        "runtime_version": "host-detected",
        "format": "GGUF",
        "quantization": "Q4_K_M",
        "hardware_id": "cpu-i5-16gb",
        "workload": "A01",
        "technical_profile_level": "T2",
        "weight_memory_gb": "1",
        "context_tokens": "2048",
        "quality_score": "80",
        "tokens_per_second": "10",
        "jgb_level": "3",
        "backend": "cpu",
        "model_artifact": {"path": MODEL_PATH, "sha256": MODEL_SHA256},
    }]

    selected = select(
        rows,
        workload="A01",
        hardware="cpu-i5-16gb",
        ram_gb=16,
        context_tokens=2048,
        top_n=1,
        required_runtime="llama.cpp",
    )
    candidate = selected["candidates"][0]

    assert candidate["runtime"] == "llama.cpp"
    assert candidate["model_format"] == "GGUF"
    assert candidate["backend"] == "cpu"
    assert candidate["model_artifact"]["path"] == MODEL_PATH
    assert candidate["model_artifact"]["sha256"] == MODEL_SHA256

    plan = resolve_runtime(
        candidate,
        runtime_commands={"llama.cpp": ["llama-cli"]},
        hardware={"os": "Linux", "ram_gb": 16, "cpu": "host"},
    )
    assert plan["execution_authorized"] is True
    assert plan["runtime"]["command"] == [
        "llama-cli", "-m", MODEL_PATH, "-c", "2048", "-p"
    ]


def test_selection_cannot_authorize_llama_cpp_without_artifact():
    rows = [{
        "model_id": "Qwen3-0.6B-Q4_K_M",
        "model_name": "Qwen3-0.6B-Q4_K_M",
        "runtime": "llama.cpp",
        "format": "GGUF",
        "quantization": "Q4_K_M",
        "hardware_id": "cpu-i5-16gb",
        "workload": "A01",
        "technical_profile_level": "T2",
        "weight_memory_gb": "1",
        "context_tokens": "2048",
        "quality_score": "80",
        "tokens_per_second": "10",
        "jgb_level": "3",
        "backend": "cpu",
    }]

    selected = select(
        rows,
        workload="A01",
        hardware="cpu-i5-16gb",
        ram_gb=16,
        context_tokens=2048,
        top_n=1,
        required_runtime="llama.cpp",
    )
    candidate = selected["candidates"][0]

    try:
        resolve_runtime(candidate, runtime_commands={"llama.cpp": ["llama-cli"]})
    except ValueError as exc:
        assert "model_artifact" in str(exc)
    else:
        raise AssertionError("llama.cpp was authorized without a model artifact")
