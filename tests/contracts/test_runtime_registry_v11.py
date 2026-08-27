from pathlib import Path
import json
import pytest

from scripts.runtime_registry import SCHEMA_VERSION, registry_entries, capability_match, get_runtime
from scripts.runtimes.v1_1_adapters import ADAPTERS
from scripts.runtime_benchmark_v1 import begin, complete
from scripts.runtime_evidence_bridge import to_evidence


def plan(runtime, **extra):
    value = {"runtime": runtime, "model_id": "org/model", "model": {"total_params_m": 7000, "active_params_m": 7000},
             "quantization": "Q4_K_M", "architecture_class": "dense", "execution_authorized": True,
             "optimization_families": [], "hardware": {}, "workload": {}}
    value.update(extra)
    return value


def test_registry_has_one_common_contract_for_all_v11_runtimes():
    entries = registry_entries()
    assert len(entries) == 11
    assert set(entries) == set(ADAPTERS)
    assert all(entry.physical_test_required for entry in entries.values())
    assert SCHEMA_VERSION == "runtime-registry.v1.1"


def test_registry_entries_are_structurally_valid():
    for entry in registry_entries().values():
        assert entry.id and entry.adapter and entry.version
        assert entry.modes and entry.architectures and entry.formats and entry.backends
        assert entry.capabilities
        assert entry.entrypoint["kind"]
        assert isinstance(entry.entrypoint["argv"], list)
        assert isinstance(entry.physical_test_required, bool)


def test_every_adapter_accepts_a_controlled_plan():
    entries = registry_entries()
    for runtime, adapter in ADAPTERS.items():
        entry = entries[runtime]
        p = plan(runtime, quantization=entry.formats[0])
        if runtime == "FreeToken":
            p.update({"architecture_class": "moe", "backend": "cuda", "model": {"total_params_b": 70, "quantized_weight_gb": 30},
                      "moe": {"is_moe": True}, "workload": {"agentic": True},
                      "hardware": {"vram_gb": 24, "ram_gb": 64, "host_memory_bandwidth_gbps": 500,
                                   "pcie_h2d_bandwidth_gbps": 20, "cpu_moe_bandwidth_gbps": 100}})
        adapter.prepare(p, entry)


def test_canonical_ollama_identifier_is_preserved():
    assert get_runtime("ollama").id == "ollama"


def test_capability_match_blocks_incompatible_runtime():
    ok, reasons = capability_match(registry_entries()["TensorRT-LLM"], backend="metal")
    assert not ok and reasons


def test_benchmark_never_turns_estimate_into_measurement():
    record = begin({"execution_authorized": True, "runtime": {"name": "vLLM", "adapter": "vllm.v1.1"},
                    "model_id": "org/model", "model": {}, "quantization": "FP8", "hardware": {},
                    "workload": {}, "estimated_tps": 123.0})
    assert record["measured"] is None
    with pytest.raises(ValueError):
        complete(record, {"estimated_tps": 123.0})
    completed = complete(record, {"measured_tps": 10.5, "ttft_ms": 20.0})
    evidence = to_evidence(completed)
    assert evidence["status"] == "measured"
    assert evidence["measurements"]["measured_tps"] == 10.5


def test_benchmark_rejects_non_numeric_measurements():
    record = begin(plan("vLLM", quantization="FP8"))
    with pytest.raises(ValueError):
        complete(record, {"measured_tps": "10.5"})


def test_benchmark_rejects_missing_execution_identity():
    with pytest.raises(ValueError):
        begin({"execution_authorized": True, "runtime": {"name": "vLLM"}, "model_id": "org/model", "quantization": "FP8"})


def test_evidence_rejects_missing_provenance():
    record = begin(plan("vLLM", quantization="FP8"))
    completed = complete(record, {"measured_tps": 10.5})
    completed["execution_id"] = None
    with pytest.raises(ValueError):
        to_evidence(completed)


def test_registry_rejects_duplicate_aliases(tmp_path: Path):
    registry = {"schema_version": SCHEMA_VERSION, "runtimes": [
        {"id": "a", "adapter": "a", "version": "1", "aliases": ["shared"], "modes": ["cpu"], "architectures": ["dense"], "formats": ["x"], "backends": ["cpu"], "capabilities": ["x"], "entrypoint": {"kind": "executable", "argv": ["a"]}, "availability": "host-detected", "metrics": "x", "physical_test_required": True},
        {"id": "b", "adapter": "b", "version": "1", "aliases": ["shared"], "modes": ["cpu"], "architectures": ["dense"], "formats": ["x"], "backends": ["cpu"], "capabilities": ["x"], "entrypoint": {"kind": "executable", "argv": ["b"]}, "availability": "host-detected", "metrics": "x", "physical_test_required": True},
    ]}
    path = tmp_path / "registry.json"
    path.write_text(json.dumps(registry), encoding="utf-8")
    with pytest.raises(ValueError):
        registry_entries(path)
