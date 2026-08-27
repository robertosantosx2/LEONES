import pytest

from scripts.ollama_a01_runtime import validate_canonical_calls


MODEL = "qwen2.5:0.5b-instruct-q4_K_M"


def test_lookup_model_rejects_extra_output_path():
    calls = [
        {
            "tool": "lookup_model",
            "arguments": {
                "model_id": MODEL,
                "output_path": "report.txt",
            },
        },
        {
            "tool": "write_report",
            "arguments": {
                "path": "report.txt",
            },
        },
    ]

    with pytest.raises(RuntimeError, match="exactly model_id"):
        validate_canonical_calls(calls, MODEL)


def test_canonical_a01_calls_are_accepted():
    calls = [
        {
            "tool": "lookup_model",
            "arguments": {
                "model_id": MODEL,
            },
        },
        {
            "tool": "write_report",
            "arguments": {
                "path": "report.txt",
            },
        },
    ]

    validate_canonical_calls(calls, MODEL)
