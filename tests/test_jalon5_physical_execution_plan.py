from scripts.runtime_gate import resolve_runtime


MODEL_PATH = "artifacts/models/Qwen3-0.6B-Q4_K_M.gguf"
MODEL_SHA256 = "b0638f08417a2d3c8652760462eb5407c6e30173cf9608ad0820757a281eea0e"


def candidate(**extra):
    value = {
        "model_id": "Qwen3-0.6B-Q4_K_M",
        "model_name": "Qwen3-0.6B-Q4_K_M",
        "runtime": "llama.cpp",
        "runtime_version": "host-detected",
        "quantization": "Q4_K_M",
        "model_format": "GGUF",
        "execution_mode": "cpu",
        "backend": "cpu",
        "selection_status": "BENCHMARK_REQUIRED",
        "rank": 1,
        "fit_score": 1.0,
        "evidence_level": "estimated",
        "optimization_families": [],
        "model_artifact": {
            "path": MODEL_PATH,
            "sha256": MODEL_SHA256,
        },
        "workload": {
            "task": "A01",
            "context_tokens": 2048,
        },
    }
    value.update(extra)
    return value


def test_jalon5_authorized_plan_materializes_physical_llama_command():
    plan = resolve_runtime(
        candidate(),
        runtime_commands={"llama.cpp": ["llama-cli"]},
        hardware={"os": "Linux", "ram_gb": 16, "cpu": "host"},
    )

    assert plan["execution_authorized"] is True
    assert plan["measurement_required"] is True
    assert plan["benchmark_probe"] is True
    assert plan["model_artifact"]["path"] == MODEL_PATH
    assert plan["model_artifact"]["sha256"] == MODEL_SHA256
    assert plan["runtime"]["entrypoint"] == ["llama-cli"]
    assert plan["runtime"]["command"] == [
        "llama-cli",
        "-m",
        MODEL_PATH,
        "-c",
        "2048",
        "-p",
    ]


def test_jalon5_plan_stays_unauthorized_without_trusted_command():
    plan = resolve_runtime(candidate())

    assert plan["execution_authorized"] is False
    assert plan["runtime"]["command"] == ["llama-cli"]
    assert plan["runtime"]["entrypoint"] == ["llama-cli"]


def test_jalon5_rejects_non_llama_trusted_executable():
    try:
        resolve_runtime(
            candidate(),
            runtime_commands={"llama.cpp": ["/tmp/not-llama"]},
        )
    except ValueError as exc:
        assert "llama-cli" in str(exc)
    else:
        raise AssertionError("invalid llama.cpp trusted executable was accepted")


def test_jalon5_rejects_llama_without_model_artifact():
    try:
        resolve_runtime(
            candidate(model_artifact=None),
            runtime_commands={"llama.cpp": ["llama-cli"]},
        )
    except ValueError as exc:
        assert "model_artifact" in str(exc)
    else:
        raise AssertionError("llama.cpp plan was authorized without model artifact")


def test_jalon5_rejects_llama_without_gguf_format():
    try:
        resolve_runtime(
            candidate(model_format="safetensors"),
            runtime_commands={"llama.cpp": ["llama-cli"]},
        )
    except ValueError as exc:
        assert "GGUF" in str(exc)
    else:
        raise AssertionError("llama.cpp plan accepted a non-GGUF artifact")
