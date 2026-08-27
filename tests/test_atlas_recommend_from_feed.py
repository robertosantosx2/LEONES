"""Pruebas de integración del recomendador con CABE/RULA.

Estas pruebas comprueban una regla importante: la clase de rendimiento se
calcula desde tok/s, pero no altera directamente el fit_score.
"""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("atlas_recommend", ROOT / "scripts" / "atlas_recommend_from_feed.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def row(tps):
    return {
        "model_id": "demo-1",
        "model_name": "Demo",
        "workload": "chat",
        "hardware_id": "i7 32GB RTX 4060",
        "estimated_memory_gb": "8",
        "weight_memory_gb": "8",
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "technical_profile_level": "T3",
        "context_tokens": "4096",
        "tokens_per_second": str(tps),
        "quality_score": "80",
        "jgb_level": "3",
    }


def test_recommendation_contains_cabe():
    result = module.recommend([row(7.5)], [], "chat", "i7 32GB RTX 4060", 32, 8, 4096, required_runtime="llama.cpp")
    assert len(result) == 1
    assert result[0][-1] == "CABE"


def test_recommendation_contains_rula_at_boundary():
    result = module.recommend([row(10)], [], "chat", "i7 32GB RTX 4060", 32, 8, 4096, required_runtime="llama.cpp")
    assert len(result) == 1
    assert result[0][-1] == "RULA"


def test_missing_performance_is_explicitly_unknown():
    item = row(7.5)
    item["tokens_per_second"] = ""
    result = module.recommend([item], [], "chat", "i7 32GB RTX 4060", 32, 8, 4096, required_runtime="llama.cpp")
    assert len(result) == 1
    assert result[0][-1] == "UNKNOWN"
