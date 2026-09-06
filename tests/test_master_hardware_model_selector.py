import json
from pathlib import Path

from scripts.select_master_hardware_model import recommend

ROOT = Path(__file__).resolve().parents[1]


def load_matrix():
    return json.loads((ROOT / "data/master_hardware_model_matrix.v1.json").read_text())


def test_high_vram_selects_highest_aa_candidate():
    result = recommend(load_matrix(), "i7_ryzen7", 32, "RTX 5090")
    assert result["status"] == "selected"
    assert result["selection"]["model_id"] == "qwen3.8-27b-xhigh"
    assert result["selection"]["aa_score"] == 52


def test_low_memory_falls_back_to_smaller_model():
    result = recommend(load_matrix(), "i5_ryzen5", 8, "GTX 1650 4GB")
    assert result["status"] == "selected"
    assert result["selection"]["model_id"] == "qwen3.5-9b-reasoning"


def test_cpu_tier_does_not_change_intelligence_selection():
    matrix = load_matrix()
    a = recommend(matrix, "i5_ryzen5", 32, "RTX 5070")
    b = recommend(matrix, "i9_ryzen9", 32, "RTX 5070")
    assert a["selection"]["model_id"] == b["selection"]["model_id"]
    assert a["selection"]["aa_score"] == b["selection"]["aa_score"]
