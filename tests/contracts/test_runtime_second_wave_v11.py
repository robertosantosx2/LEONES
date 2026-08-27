import pytest

from scripts.runtime_registry import registry_entries
from scripts.runtimes.v1_1_adapters import ADAPTERS


CPD_WAVE = {
    "vLLM": {"format": "safetensors", "mode": "serving", "backend": "cuda", "architecture": "dense"},
    "SGLang": {"format": "safetensors", "mode": "serving", "backend": "cuda", "architecture": "dense"},
}

ARCHIVED_WAVE = {"MLX/MLX-LM", "ExLlama", "OpenVINO", "ONNX Runtime GenAI", "TensorRT-LLM"}


def controlled_plan(runtime, spec):
    return {
        "runtime": {"name": runtime, "adapter": ADAPTERS[runtime].adapter_id},
        "model_id": "fixture/cpd-wave-model",
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


def test_cpd_wave_has_exactly_two_operational_adapters():
    entries = registry_entries()
    assert set(CPD_WAVE) == {"vLLM", "SGLang"}
    assert set(CPD_WAVE) <= set(entries)
    assert set(CPD_WAVE) <= set(ADAPTERS)


def test_archived_wave_is_preserved_as_adapter_knowledge_only():
    entries = registry_entries()
    assert ARCHIVED_WAVE.isdisjoint(entries)
    assert ARCHIVED_WAVE <= set(ADAPTERS)


@pytest.mark.parametrize("runtime", CPD_WAVE)
def test_cpd_adapter_is_declarative_and_host_gated(runtime):
    entries = registry_entries()
    adapter = ADAPTERS[runtime]
    entry = entries[runtime]
    spec = CPD_WAVE[runtime]

    prepared = adapter.prepare(controlled_plan(runtime, spec), entry)

    assert prepared.runtime_id == runtime
    assert prepared.adapter_id == adapter.adapter_id
    assert prepared.model_ref == "fixture/cpd-wave-model"
    assert prepared.metadata["host_requirements"]
    assert prepared.metadata["physical_test_required"] is True
    assert prepared.metadata["metrics"] == entry.metrics


@pytest.mark.parametrize("runtime", CPD_WAVE)
def test_cpd_adapter_rejects_wrong_backend(runtime):
    entries = registry_entries()
    adapter = ADAPTERS[runtime]
    spec = CPD_WAVE[runtime].copy()
    spec["backend"] = "metal"

    with pytest.raises(ValueError):
        adapter.prepare(controlled_plan(runtime, spec), entries[runtime])


@pytest.mark.parametrize("runtime", CPD_WAVE)
def test_cpd_adapter_rejects_registry_adapter_mismatch(runtime):
    entries = registry_entries()
    entry = entries[runtime]
    spec = CPD_WAVE[runtime]
    plan = controlled_plan(runtime, spec)
    plan["runtime"]["adapter"] = "not-the-registered-adapter"

    with pytest.raises(ValueError):
        ADAPTERS[runtime].prepare(plan, entry)
