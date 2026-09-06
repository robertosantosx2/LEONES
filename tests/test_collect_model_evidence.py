from __future__ import annotations
import pytest
from scripts.collect_model_evidence import build_feed, detect_formats, detect_quantizations, estimate_fit, estimate_weight_memory_gb, extract_context, extract_parameter_count, normalize_purposes

def test_rc4_requires_non_empty_user_intent() -> None:
    with pytest.raises(ValueError): normalize_purposes([])

def test_user_intent_is_multiple_and_normalized() -> None:
    assert normalize_purposes(["coding", "research", "reasoning", "coding"]) == ["programming", "research", "reasoning"]

def test_extract_hf_architecture_signals() -> None:
    info={"config":{"num_parameters":7_000_000_000,"max_position_embeddings":32768,"torch_dtype":"bfloat16"},"safetensors":{"parameters":{"total":7_000_000_000}},"tags":["text-generation"],"siblings":[{"rfilename":"model-q4_k_m.gguf"},{"rfilename":"model.safetensors"}]}
    assert extract_parameter_count(info)==7.0
    assert extract_context(info)==32768
    assert "gguf" in detect_formats(info)
    assert "safetensors" in detect_formats(info)
    assert "q4_k_m" in detect_quantizations(info)

def test_weight_estimate_is_weight_only_prefilter() -> None:
    assert round(estimate_weight_memory_gb(7.0,4.5),2)==3.67
    result=estimate_fit(parameters_b=7.0,ram_gb=16.0,vram_gb=8.0,quantization="q4_k_m")
    assert result["prefilter_status"]=="fits"
    assert result["method"]=="weights_only_prefilter_1.20x"

def test_build_feed_accepts_100_models_for_fitllm() -> None:
    models=[{"model_id":f"org/model-{i}","parameters_b":7.0,"quantizations":["q4_k_m"],"formats":["gguf"],"downloads_30d":1000} for i in range(100)]
    feed=build_feed(hardware={"ram_gb":16,"vram_gb":8},purposes=["programming","research"],hf_models=models,aa_models=[],aa_index_version=None,limit=100)
    assert feed["fitllm_input"]["max_models"]==100
    assert feed["fitllm_input"]["model_count"]==100
    assert len(feed["fitllm_input"]["model_evidence"])==100

def test_build_feed_rejects_more_than_100() -> None:
    with pytest.raises(ValueError):
        build_feed(hardware={"ram_gb":16},purposes=["research"],hf_models=[],aa_models=[],aa_index_version=None,limit=101)
