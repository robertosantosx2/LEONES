import pytest

from scripts.runtime_registry import registry_entries
from scripts.runtimes.v1_1_adapters import ADAPTERS


SECOND_WAVE = {
    "vLLM": {"format": "safetensors", "mode": "serving", "backend": "cuda", "architecture": "dense"},
    "SGLang": {"format": "safetensors", "mode": "serving", "backend": "cuda", "architecture": "dense"},
    "MLX/MLX-LM": {"format": "safetensors", "mode": "unified-memory", "backend": "metal", "architecture": "dense"},
    "ExLlama": {"format": "EXL2", "mode": "gpu", "backend": "cuda", "architecture": "dense"},
    "OpenVINO": {"format": "OpenVINO", "mode": "cpu", "backend": "cpu", "architecture": "dense"},
    "ONNX Runtime GenAI": {"format": "ONNX", "mode": "cpu", "backend": "cpu", "architecture": "dense"},
    "TensorRT-LLM": {"format": "safetensors", "mode": "serving", "backend": "cuda", "architecture": "dense"},
}


def controlled_plan(runtime, spec):
    return {
        "runtime": {"name": runtime, "adapter": ADAPTERS[runtime].adapter_id},
        "model_id": "fixture/second-wave-model",
        "quantization": spec["format"],
        "model_format": spec["format"],
        "architecture_class": spec["architecture"],
        "execution_mode": spec["mode"],
        "backend": spec["backend"],
        "execution_authorized": True,
        "required_capabilities": [],
        "hardware": {},
        "workload": {},
    }


def test_second_wave_has_exactly_seven_registered_adapters():
    entries = registry_entries()
    assert set(SECOND_WAVE) <= set(entries)
    assert set(SECOND_WAVE) <= set(ADAPTERS)


@pytest.mark.parametrize("runtime", SECOND_WAVE)
def test_second_wave_adapter_is_declarative_and_host_gated(runtime):
    entries = registry_entries()
    adapter = ADAPTERS[runtime]
    entry = entries[runtime]
    spec = SECOND_WAVE[runtime]

    prepared = adapter.prepare(controlled_plan(runtime, spec), entry)

    assert prepared.runtime_id == runtime
    assert prepared.adapter_id == adapter.adapter_id
    assert prepared.model_ref == "fixture/second-wave-model"
    assert prepared.metadata["host_requirements"]
    assert prepared.metadata["physical_test_required"] is True
    assert prepared.metadata["metrics"] == entry.metrics


@pytest.mark.parametrize("runtime", SECOND_WAVE)
def test_second_wave_adapter_rejects_wrong_backend(runtime):
    entries = registry_entries()
    adapter = ADAPTERS[runtime]
    spec = SECOND_WAVE[runtime].copy()
    wrong_backend = "metal" if spec["backend"] != "metal" else "cuda"
    spec["backend"] = wrong_backend

    with pytest.raises(ValueError):
        adapter.prepare(controlled_plan(runtime, spec), entries[runtime])


@pytest.mark.parametrize("runtime", SECOND_WAVE)
def test_second_wave_adapter_rejects_registry_adapter_mismatch(runtime):
    entries = registry_entries()
    entry = entries[runtime]
    spec = SECOND_WAVE[runtime]
    plan = controlled_plan(runtime, spec)
    plan["runtime"]["adapter"] = "not-the-registered-adapter"

    with pytest.raises(ValueError):
        ADAPTERS[runtime].prepare(plan, entry)
