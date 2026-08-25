from scripts.runtime_gate import gate_selection, resolve_runtime


def candidate(status="TOP_N", **extra):
    value = {"model_id": "example/model", "runtime": "llama.cpp", "quantization": "Q4_K_M", "selection_status": status, "rank": 1, "fit_score": 0.8, "evidence_level": "T3", "llmfit": {"estimated_tps": 12.0}}
    value.update(extra)
    return value


def test_top_n_is_not_execution_authorized_without_trusted_command():
    plan = resolve_runtime(candidate())
    assert plan["execution_authorized"] is False
    assert plan["benchmark_probe"] is False
    assert plan["measured_tps"] is None


def test_benchmark_required_is_probe_but_not_authorized_without_trusted_command():
    plan = resolve_runtime(candidate("BENCHMARK_REQUIRED"))
    assert plan["execution_authorized"] is False
    assert plan["benchmark_probe"] is True
    assert plan["measurement_required"] is True


def test_trusted_command_authorizes_execution():
    plan = resolve_runtime(candidate(), runtime_commands={"llama.cpp": ["llama-server"]})
    assert plan["execution_authorized"] is True


def test_rejected_candidate_is_blocked():
    result = gate_selection({"candidates": [candidate("REJECTED")]})
    assert result["counts"] == {"plans": 0, "blocked": 1}


def test_runtime_availability_is_checked():
    result = gate_selection({"candidates": [candidate()]}, available_runtimes={"vllm"})
    assert result["counts"] == {"plans": 0, "blocked": 1}


def test_runtime_plan_preserves_estimate_without_measurement():
    plan = resolve_runtime(candidate())
    assert plan["estimated_tps"] == 12.0
    assert plan["measured_tps"] is None
