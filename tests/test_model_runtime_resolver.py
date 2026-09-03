from runtime_selection.model_runtime_resolver import resolve_model_runtime


def test_gguf_candidate_resolves_to_llama_cpp():
    result = resolve_model_runtime({"model_id": "org/Qwen3-4B-GGUF"})
    assert result.status == "RESOLVED"
    assert result.model_format == "GGUF"
    assert result.runtime_id == "llama.cpp"
    assert result.runtime_model_ref is None


def test_explicit_ollama_rejects_hugging_face_gguf_id():
    result = resolve_model_runtime(
        {"model_id": "org/Qwen3-4B-GGUF", "runtime": "ollama"}
    )
    assert result.status == "BLOCKED"
    assert "Ollama" in (result.reason or "")
    assert result.runtime_model_ref is None


def test_ollama_managed_reference_is_preserved():
    result = resolve_model_runtime(
        {"model_id": "qwen2.5:0.5b-instruct-q4_K_M", "runtime": "ollama", "model_format": "Ollama-managed"}
    )
    assert result.status == "RESOLVED"
    assert result.runtime_id == "ollama"
    assert result.runtime_model_ref == "qwen2.5:0.5b-instruct-q4_K_M"


def test_resolution_does_not_claim_installation_or_measurement():
    result = resolve_model_runtime({"model_id": "org/Qwen3-4B-GGUF"})
    payload = result.to_dict()
    assert payload["status"] == "RESOLVED"
    assert "installed" not in payload
    assert "measured_tps" not in payload


def test_unavailable_runtime_is_not_resolved():
    result = resolve_model_runtime(
        {"model_id": "org/Qwen3-4B-GGUF"}, available_runtimes={"ollama"}
    )
    assert result.status == "RUNTIME_UNAVAILABLE"
    assert result.runtime_id == "llama.cpp"
