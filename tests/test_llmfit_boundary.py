import pytest

from scripts.integrations.llmfit import assert_not_measured, normalize_result


def test_llmfit_is_normalized_as_estimated():
    result = normalize_result(
        {
            "hardware": {"ram_gb": 16},
            "candidate": {
                "id": "model-1",
                "name": "Model 1",
                "fit": "good",
                "estimated_speed": 12.5,
                "memory_gb": 8,
                "context": 8192,
                "quant": "Q4_K_M",
                "runtime": "llama.cpp",
            },
        },
        source_version="test",
        observed_at="2026-08-28T00:00:00Z",
    )

    assert result["source"] == "llmfit"
    assert result["provenance"]["kind"] == "estimated"
    assert result["candidate"]["estimated_tps"] == 12.5
    assert "measured_tps" not in result["candidate"]
    assert_not_measured(result)


def test_llmfit_rejects_empty_provenance():
    with pytest.raises(ValueError):
        normalize_result({}, source_version="", observed_at="2026-08-28T00:00:00Z")


def test_llmfit_cannot_be_promoted_to_measured():
    record = normalize_result({}, source_version="test", observed_at="2026-08-28T00:00:00Z")
    record["candidate"]["measured_tps"] = 99
    with pytest.raises(ValueError, match="measured_tps"):
        assert_not_measured(record)
