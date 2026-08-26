from scripts.model_selector import select


def test_cpu_only_profile_does_not_require_gpu():
    result = select(
        [
            {
                "model_id": "cpu-demo",
                "model_name": "CPU Demo",
                "technical_profile_level": "T2",
                "runtime": "llama.cpp",
                "quantization": "Q4_K_M",
                "weight_memory_gb": "6",
                "context_tokens": "4096",
                "quality_score": "70",
                "is_moe": "false",
                "agentic": "true",
            }
        ],
        workload="agentic",
        hardware="cpu-only",
        ram_gb=16,
        vram_gb=0,
        required_runtime="llama.cpp",
        top_n=1,
    )

    assert result["counts"]["eligible"] == 1
    candidate = result["candidates"][0]
    assert candidate["hardware_fit"] == "compatible"
    assert candidate["runtime_fit"] == "preselected"
    assert result["selection_policy"]["vram_gb"] == 0
    assert candidate["llmfit"] is None
    assert candidate["selection_status"] == "BENCHMARK_REQUIRED"


def test_cpu_only_cannot_invent_gpu_capability():
    result = select(
        [
            {
                "model_id": "cpu-demo",
                "model_name": "CPU Demo",
                "technical_profile_level": "T2",
                "runtime": "llama.cpp",
                "weight_memory_gb": "4",
            }
        ],
        workload="chat",
        hardware="cpu-only",
        ram_gb=16,
        vram_gb=0,
        required_runtime="llama.cpp",
    )
    assert result["selection_policy"]["vram_gb"] == 0
    assert all("vram_gb" not in candidate for candidate in result["candidates"])
