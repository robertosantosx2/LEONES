from scripts.selection_pipeline import build_pipeline
from scripts.fit_consensus import CATEGORIES, SOURCES


def fit_sources():
    payload = {}
    for source in SOURCES:
        candidates = []
        for category in CATEGORIES:
            for model_id, parameters in (("org/model", 7), ("m2", 8), ("m3", 13), ("m4", 34), ("m5", 70), ("m6", 120)):
                candidates.append({"model_id": f"{model_id}-{category}" if model_id != "org/model" else "org/model", "category": category, "parameters_b": parameters, "fit": "Good"})
        payload[source] = {"candidates": candidates}
    return payload


def test_pipeline_connects_profile_selector_and_gate():
    profile = {
        "cpu": {"model": "Intel Core i5-1035G1"},
        "memory": {"available_bytes": 7 * 1024**3},
    }
    rows = [{
        "model_id": "org/model", "model_name": "Model", "workload": "chat",
        "hardware_id": "", "technical_profile_level": "T3",
        "runtime": "llama.cpp", "quantization": "Q4_K_M",
        "format": "GGUF",
        "model_artifact": {
            "path": "artifacts/models/test.gguf",
            "sha256": "a" * 64,
        },
        "estimated_memory_gb": "4", "context_tokens": "4096",
        "quality_score": "80", "tokens_per_second": "10", "jgb_level": "4",
    }]
    import scripts.selection_pipeline as pipeline
    original = pipeline.load_rows
    pipeline.load_rows = lambda _: rows
    try:
        result = build_pipeline(
            workload="chat", feed=__import__("pathlib").Path("unused.csv"), context=4096, top_n=1,
            runtime="llama.cpp", optimizations=[], fit_sources=fit_sources(), hardware=profile,
        )
    finally:
        pipeline.load_rows = original
    assert result["selection"]["counts"]["eligible"] == 1
    assert result["runtime_selection"]["counts"]["plans"] == 1
