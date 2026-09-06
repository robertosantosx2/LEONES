from __future__ import annotations

import pytest

from scripts.collect_model_evidence import (
    build_feed,
    detect_formats,
    detect_quantizations,
    estimate_fit,
    estimate_weight_memory_gb,
    extract_context,
    extract_parameter_count,
    normalize_purposes,
)


def test_rc4_requires_non_empty_user_intent() -> None:
    with pytest.raises(ValueError):
        normalize_purposes([])


def test_user_intent_is_multiple_and_normalized() -> None:
    assert normalize_purposes(["coding", "research", "reasoning", "coding"]) == [
        "programming",
        "research",
        "reasoning",
    ]


def test_extract_hf_architecture_signals() -> None:
    info = {
        "config": {
            "num_parameters": 7_000_000_000,
            "max_position_embeddings": 32768,
            "torch_dtype": "bfloat16",
        },
        "safetensors": {"parameters": {"total": 7_000_000_000}},
        "tags": ["text-generation"],
        "siblings": [
            {"rfilename": "model-q4_k_m.gguf"},
            {"rfilename": "model.safetensors"},
        ],
    }
    assert extract_parameter_count(info) == 7.0
    assert extract_context(info) == 32768
    assert "gguf" in detect_formats(info)
    assert "safetensors" in detect_formats(info)
    assert "q4_k_m" in detect_quantizations(info)


def test_weight_estimate_is_weight_only_prefilter() -> None:
    assert round(estimate_weight_memory_gb(7.0, 4.5), 2) == 3.67
    result = estimate_fit(
        parameters_b=7.0,
        ram_gb=16.0,
        vram_gb=8.0,
        quantization="q4_k_m",
    )
    assert result["prefilter_status"] == "fits"
    assert result["method"] == "weights_only_prefilter_1.20x"


def test_build_feed_preserves_two_source_roles() -> None:
    feed = build_feed(
        hardware={"ram_gb": 16, "vram_gb": 8},
        purposes=["programming", "research"],
        hf_models=[
            {
                "model_id": "org/model-7b",
                "parameters_b": 7.0,
                "quantizations": ["q4_k_m"],
                "formats": ["gguf"],
                "downloads_30d": 1000,
            }
        ],
        aa_models=[
            {
                "id": "aa-1",
                "name": "org/model-7b",
                "slug": "org-model-7b",
                "evaluations": {
                    "artificial_analysis_intelligence_index": 50.0,
                    "artificial_analysis_coding_index": 60.0,
                },
                "performance": {"median_output_tokens_per_second": 40.0},
            }
        ],
        aa_index_version=4.2,
        limit=10,
    )
    assert feed["schema"] == "leones.rc4.model-evidence.v1"
    assert feed["user_intent"]["selection_mode"] == "multiple"
    assert feed["user_intent"]["purposes"] == ["programming", "research"]
    assert feed["status"] == "estimated"
    assert feed["measurement_required"] is True
    assert feed["candidates"][0]["hf"]["model_id"] == "org/model-7b"
    assert feed["candidates"][0]["artificial_analysis"]["name"] == "org/model-7b"
