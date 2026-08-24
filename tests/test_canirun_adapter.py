from router.canirun_adapter import (
    build_hardware,
    normalize_compatibility,
    normalize_recommendations,
)


def test_normalize_compatibility_keeps_external_estimates_separate():
    candidate = normalize_compatibility(
        {
            "compatible": True,
            "status": "comfortable",
            "grade": "A",
            "score": 84,
            "modelId": "llama3.1-8b",
            "modelName": "Llama 3.1 8B",
            "quantization": "Q4_K_M",
            "recommendedQuantization": "Q4_K_M",
            "estimated": {
                "tokensPerSecond": 22.5,
                "modelSizeGb": 4.9,
                "vramRequiredGb": 5.2,
                "ramRequiredGb": 8,
                "memoryHeadroomGb": 6.8,
            },
        }
    )

    assert candidate.source == "canirun"
    assert candidate.estimate_status == "estimated"
    assert candidate.estimated_tps == 22.5
    assert candidate.measured_tps is None
    assert candidate.measurement_status == "not-measured"
    assert candidate.grade == "A"


def test_normalize_recommendations_uses_recommendation_list():
    result = normalize_recommendations(
        {
            "count": 1,
            "recommendations": [
                {
                    "modelId": "qwen3-8b",
                    "name": "Qwen3 8B",
                    "quantization": "Q4_K_M",
                    "status": "comfortable",
                    "grade": "S",
                    "score": 91,
                    "estimatedTokensPerSecond": 31.2,
                    "vramRequiredGb": 5.0,
                }
            ],
        }
    )

    assert len(result) == 1
    assert result[0]["model_id"] == "qwen3-8b"
    assert result[0]["source"] == "canirun"
    assert result[0]["estimated_tps"] == 31.2
    assert result[0]["measured_tps"] is None


def test_build_hardware_matches_canirun_public_shape():
    hardware = build_hardware(
        ram_gb=32,
        gpu_name="NVIDIA RTX 3060",
        vram_gb=12,
        memory_bandwidth_gbps=360,
    )

    assert hardware["ramGb"] == 32
    assert hardware["gpu"]["name"] == "NVIDIA RTX 3060"
    assert hardware["gpu"]["vramGb"] == 12
    assert hardware["gpu"]["memoryBandwidthGbps"] == 360
