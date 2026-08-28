import json
from pathlib import Path

from scripts.runtime_gate import resolve_runtime
from scripts.runtime_registry import capability_match, registry_entries


def test_registry_has_complete_deployment_taxonomy():
    data = json.loads(Path("runtime_registry.v1.1.json").read_text(encoding="utf-8"))
    allowed = set(data["taxonomy"]["deployment_class"])
    profiles = set(data["taxonomy"]["serving_profile"])
    entries = registry_entries()
    assert len(entries) == 11
    assert list(entries) == [
        "llama.cpp", "FreeToken", "AirLLM", "ollama", "vLLM", "SGLang",
        "MLX/MLX-LM", "ExLlama", "OpenVINO", "ONNX Runtime GenAI", "TensorRT-LLM",
    ]
    for entry in entries.values():
        assert entry.deployment_class
        assert set(entry.deployment_class) <= allowed
        assert entry.serving_profiles
        assert set(entry.serving_profiles) <= profiles


def test_datacenter_profile_filters_out_local_runtimes():
    entries = registry_entries()
    ok, reasons = capability_match(entries["ollama"], deployment_class="datacenter")
    assert not ok
    assert any("deployment class" in reason for reason in reasons)
    ok, reasons = capability_match(
        entries["vLLM"],
        deployment_class="datacenter",
        serving_profile="multi_user",
    )
    assert ok
    assert reasons == []


def test_local_profile_keeps_workstation_runtimes():
    entries = registry_entries()
    ok, reasons = capability_match(
        entries["FreeToken"],
        deployment_class="workstation",
        serving_profile="single_user",
    )
    assert ok
    assert reasons == []


def _candidate(runtime: str, **extra):
    value = {
        "model_id": "example/model",
        "runtime": runtime,
        "quantization": "Q4_K_M",
        "selection_status": "TOP_N",
        "rank": 1,
        "fit_score": 0.8,
        "evidence_level": "T3",
        "llmfit": {"estimated_tps": 12.0},
        "optimization_families": [],
    }
    value.update(extra)
    return value


def test_gate_accepts_matching_deployment_profile():
    plan = resolve_runtime(
        _candidate("vLLM", deployment_class="datacenter", serving_profile="multi_user"),
        runtime_commands={"vLLM": ["trusted-vllm"]},
    )
    assert plan["execution_authorized"] is True


def test_gate_blocks_incompatible_deployment_profile():
    try:
        resolve_runtime(
            _candidate("ollama", deployment_class="datacenter"),
            runtime_commands={"ollama": ["trusted-ollama"]},
        )
    except ValueError as exc:
        assert "deployment class unsupported" in str(exc)
    else:
        raise AssertionError("incompatible deployment profile was accepted")
