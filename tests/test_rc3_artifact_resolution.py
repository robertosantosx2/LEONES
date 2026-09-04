import pytest

from runtime_selection.artifact_resolution import resolve_artifact, validate_artifact


CANDIDATE = {
    "model_id": "Qwen/Qwen3.5-0.8B",
    "name": "Qwen3.5 0.8B Reasoning",
    "parameters_b": 0.9,
    "quantization_bits": 4,
}


def test_source_resolution_is_not_executable():
    record = resolve_artifact(
        CANDIDATE,
        source_repo="bartowski/Qwen_Qwen3.5-0.8B-GGUF",
        artifact_format="GGUF",
    )
    validate_artifact(record)
    assert record["artifact"]["status"] == "source_resolved"
    assert record["executable"] is False
    assert record["download_performed"] is False
    assert record["resolution_required_before_execution"] is True


def test_concrete_artifact_requires_identity():
    record = resolve_artifact(
        CANDIDATE,
        source_repo="bartowski/Qwen_Qwen3.5-0.8B-GGUF",
        artifact_format="GGUF",
        artifact_filename="Qwen_Qwen3.5-0.8B-Q4_K_M.gguf",
        revision="example-revision",
        sha256="a" * 64,
    )
    validate_artifact(record)
    assert record["artifact"]["status"] == "resolved"
    assert record["executable"] is True


def test_resolved_without_identity_is_rejected():
    record = resolve_artifact(
        CANDIDATE,
        source_repo="bartowski/Qwen_Qwen3.5-0.8B-GGUF",
        artifact_format="GGUF",
    )
    record["artifact"]["status"] = "resolved"
    with pytest.raises(ValueError, match="requires filename, revision and sha256"):
        validate_artifact(record)
