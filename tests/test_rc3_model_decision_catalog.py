import json
from pathlib import Path

from runtime_selection.decision_engine import decide_models


ROOT = Path(__file__).resolve().parents[1]
CATALOG = json.loads((ROOT / "runtime_selection/data/model-evidence.rc3.json").read_text(encoding="utf-8"))


def hardware():
    return {
        "schema": "hardware-profile.v1",
        "verification": "detected",
        "ram": {"total_gb": 7.031, "available_gb": 2.201},
        "cpu": {"model": "Intel(R) Core(TM) i5-1035G1 CPU @ 1.00GHz", "logical_cpus": 8, "physical_cores": 4},
        "gpu": [{"vendor_device_id": "8086:8a56", "driver": "i915"}],
        "vram_gb": None,
    }


def test_real_catalog_balanced_recommends_small_fit_model():
    result = decide_models(CATALOG, "balanced", hardware())
    assert result["recommended_model_id"] == "Qwen/Qwen3.5-0.8B"
    phi = next(c for c in result["candidates"] if c["model_id"] == "microsoft/Phi-4-mini-instruct")
    assert phi["local_fit_estimate"]["status"] == "insufficient"
    assert result["execution_authorized"] is False
    assert result["measured"] is False


def test_quality_profile_still_respects_hardware_signal():
    result = decide_models(CATALOG, "quality", hardware())
    assert result["recommended_model_id"] == "Qwen/Qwen3.5-0.8B"
    assert result["selected_model_id"] is None
