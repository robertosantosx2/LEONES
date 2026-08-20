from scripts.selection_pipeline import build_pipeline


def test_pipeline_connects_profile_selector_and_gate():
    profile = {
        "cpu": {"model": "Intel Core i5-1035G1"},
        "memory": {"available_bytes": 7 * 1024**3},
    }
    rows = [{
        "model_id": "org/model", "model_name": "Model", "workload": "chat",
        "hardware_id": "", "technical_profile_level": "T3",
        "runtime": "llama.cpp", "quantization": "Q4_K_M",
        "estimated_memory_gb": "4", "context_tokens": "4096",
        "quality_score": "80", "tokens_per_second": "10", "jgb_level": "4",
    }]
    # build_pipeline normally reads the feed; patch the helper at the module boundary.
    import scripts.selection_pipeline as pipeline
    original = pipeline.load_rows
    pipeline.load_rows = lambda _: rows
    try:
        result = build_pipeline(workload="chat", feed=__import__("pathlib").Path("unused.csv"), context=4096, top_n=1, hardware=profile)
    finally:
        pipeline.load_rows = original
    assert result["selection"]["counts"]["eligible"] == 1
    assert result["runtime_gate"]["counts"]["plans"] == 1
