import json

import pytest

# RC3 deliberately removes the LLMFit implementation adapter. Keep this
# historical test file for audit context, but do not collect it in RC3.
pytest.importorskip(
    "runtime_selection.llmfit",
    reason="LLMFit/FitLLM is outside the canonical RC3 implementation",
)

from runtime_selection.llmfit import (
    LLMFitError,
    LLMFitResult,
    build_recommend_command,
    normalise_candidates,
    normalise_hardware,
)


def test_build_recommend_command_is_read_only_json():
    assert build_recommend_command(limit=3, use_case="coding", max_context=8192) == [
        "llmfit",
        "recommend",
        "--json",
        "--limit",
        "3",
        "--use-case",
        "coding",
        "--max-context",
        "8192",
    ]


def test_normalisation_preserves_unknowns_and_estimates():
    result = LLMFitResult(
        command=("llmfit", "recommend", "--json"),
        version="1.1.12",
        system={"cpu": "Example CPU", "ram_gb": 32},
        models=[
            {
                "name": "Qwen/example",
                "fit": "good",
                "estimated_tps": 42.0,
                "quantization": "Q4_K_M",
            }
        ],
        raw={"version": "1.1.12"},
    )

    hardware = normalise_hardware(result)
    candidates = normalise_candidates(result)

    assert hardware["source"] == "llmfit"
    assert hardware["cpu"] == "Example CPU"
    assert hardware["gpu"] is None
    assert candidates[0]["model"] == "Qwen/example"
    assert candidates[0]["estimated_tps"] == 42.0
    assert candidates[0]["quantization"] == "Q4_K_M"
    assert candidates[0]["source"] == "llmfit"


def test_invalid_limit_is_rejected():
    with pytest.raises(ValueError):
        build_recommend_command(limit=0)
