from scripts.runtime_gate import gate_selection, resolve_runtime


MODEL_ARTIFACT = {
    "path": "/models/example.gguf",
    "sha256": "a" * 64,
}


def candidate(status="TOP_N", **extra):
    value = {
        "model_id": "example/model",
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "model_format": "GGUF",
        "model_artifact": MODEL_ARTIFACT,
        "selection_status": status,
        "rank": 1,
        "fit_score": 0.8,
        "evidence_level": "T3",
        "llmfit": {"estimated_tps": 12.0},
        "optimization_families": [],
        "backend": "cpu",
    }
    value.update(extra)
    return value


def test_top_n_can_execute():
    plan = resolve_runtime(candidate(), runtime_commands={"llama.cpp": ["llama-cli"]})
    assert plan["execution_authorized"] is True
    assert plan["benchmark_probe"] is False
    assert plan["measured_tps"] is None


def test_benchmark_required_is_executable_as_probe():
    plan = resolve_runtime(candidate("BENCHMARK_REQUIRED"), runtime_commands={"llama.cpp": ["llama-cli"]})
    assert plan["execution_authorized"] is True
    assert plan["benchmark_probe"] is True
    assert plan["measurement_required"] is True


def test_rejected_candidate_is_blocked():
    result = gate_selection({"candidates": [candidate("REJECTED")]})
    assert result["counts"] == {"plans": 0, "blocked": 1}


def test_runtime_availability_is_checked():
    result = gate_selection({"candidates": [candidate()]}, available_runtimes={"vllm"})
    assert result["counts"] == {"plans": 0, "blocked": 1}


def test_runtime_plan_preserves_estimate_without_measurement():
    plan = resolve_runtime(candidate(), runtime_commands={"llama.cpp": ["llama-cli"]})
    assert plan["estimated_tps"] == 12.0
    assert plan["measured_tps"] is None
