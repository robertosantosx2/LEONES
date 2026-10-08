from pathlib import Path
import sys
import types

API_ROOT = Path(__file__).resolve().parents[1] / "ods" / "extensions" / "services" / "dashboard-api"
sys.path.insert(0, str(API_ROOT))


def _stub_module(name, **attributes):
    module = types.ModuleType(name)
    for key, value in attributes.items():
        setattr(module, key, value)
    sys.modules[name] = module
    return module


class _Dummy:
    pass


class _AgentClientError(Exception):
    pass


async def _request_agent_json(*args, **kwargs):
    return {}


# This evidence-store unit test exercises the real staged helpers.py functions
# without importing the entire ODS service graph. It runs in its own pytest
# process, so these minimal dependency stubs cannot leak into other test files.
_stub_module(
    "config",
    SERVICES={}, INSTALL_DIR="/tmp/ods-icd-test", DATA_DIR="/tmp/ods-icd-test",
    LLM_BACKEND="llama-server", EXTENSIONS_DIR="/tmp/ods-icd-test/extensions",
    GPU_BACKEND="cpu", LIBRARY_MANAGEABLE_BUILTINS=set(),
    load_extension_manifests=lambda: [], read_live_env_value=lambda *args, **kwargs: None,
)
_stub_module("env_values", parse_env_value=lambda value: value)
_stub_module(
    "host_metrics",
    apple_host_metrics=lambda: {}, linux_scope=lambda: "linux",
    windows_host_metrics=lambda: {},
)
_stub_module(
    "host_agent_client",
    AgentClientError=_AgentClientError, AgentHTTPError=_AgentClientError,
    async_request_json=_request_agent_json,
)
_stub_module(
    "models", ServiceStatus=_Dummy, DiskUsage=_Dummy, ModelInfo=_Dummy,
    BootstrapStatus=_Dummy,
)
_stub_module("service_health_dns", ServiceHealthResolver=_Dummy)

import helpers


def test_icd_measurements_are_partitioned_by_exact_configuration_and_workload(tmp_path, monkeypatch):
    monkeypatch.setattr(helpers, "_PERF_FILE", tmp_path / "model-performance.json")

    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 42.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_benchmark",
        configuration_id="config-a",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 18.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_benchmark",
        configuration_id="config-b",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 99.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_metric",
    )

    icd = helpers.get_inference_configuration_measurements(
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    assert {item["configuration_id"] for item in icd} == {"config-a", "config-b"}
    assert all(item["evidence_type"] == "measured" for item in icd)
    assert {item["measured_tps"] for item in icd} == {42.0, 18.0}

    wrong_workload = helpers.get_inference_configuration_measurements(
        workload_id="dashboard-local-benchmark-v1:max_tokens=512",
    )
    assert wrong_workload == []

    model_level = helpers.get_model_performance_samples()
    assert model_level
    assert all(item["tokens_per_second"] == 99.0 for item in model_level)
    assert all(not item.get("configuration_id") for item in model_level)

    exact = helpers.get_recorded_model_performance(
        "demo-model", "Test GPU", "nvidia",
        context_length=4096,
        gguf="demo-model.gguf",
        vram_total_mb=4096,
        configuration_id="config-a",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    assert exact is not None
    assert exact["configuration_id"] == "config-a"
    assert exact["workload_id"] == "dashboard-local-benchmark-v1:max_tokens=128"
