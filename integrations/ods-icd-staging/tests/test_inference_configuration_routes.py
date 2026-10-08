from pathlib import Path
import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[1] / "ods" / "extensions" / "services" / "dashboard-api"
sys.path.insert(0, str(API_ROOT))

# Keep the staging test isolated from ODS's production security module, whose
# import can create a temporary API-key file when no key is configured.
security_stub = types.ModuleType("security")
security_stub.verify_api_key = lambda: None
sys.modules["security"] = security_stub

from routers.inference_configurations import create_inference_configuration_router
from cafe_llama_icd import validate_cafe_configuration
from security import verify_api_key


@pytest.fixture()
def harness():
    profile = {
        "runtime": "cafe-llama.cpp",
        "runtime_revision": "test-revision",
        "kernel": "baseline",
        "quantization": "Q4_K_M",
        "context_length": 4096,
        "gpu_layers": 12,
        "kv_cache": "f16",
        "flash_attention": True,
        "offload": "none",
        "speculation": "none",
        "draft_tokens": 0,
        "batch": 1,
    }
    model = {"id": "demo-model", "runtime_profiles": [profile]}
    applied = {}
    recreated = []

    def find_model(model_id):
        return model if model_id == "demo-model" else None

    def profiles_for(_model):
        return _model.get("runtime_profiles", [])

    def apply_environment(env):
        applied.update(env)
        return True

    def recreate_services(service_ids):
        recreated.append(service_ids)
        return True

    app = FastAPI()
    app.include_router(create_inference_configuration_router(
        find_model=find_model,
        get_runtime_profiles=profiles_for,
        apply_environment=apply_environment,
        recreate_services=recreate_services,
        can_apply=lambda: True,
        get_measurements=lambda model_id, workload_id: [],
    ))
    app.dependency_overrides[verify_api_key] = lambda: "test-api-key"
    return TestClient(app), applied, recreated


def test_get_discovers_configs_and_never_claims_measurements(harness):
    client, _, _ = harness
    response = client.get("/api/models/demo-model/inference-configurations")

    assert response.status_code == 200
    body = response.json()
    assert body["model_id"] == "demo-model"
    assert body["configurations"]
    assert body["measurement_required"] is True
    assert body["execution_authorized"] is False
    assert body["ranked_measured_configurations"] == []
    for item in body["configurations"]:
        assert item["measurement_required"] is True
        assert item["execution_authorized"] is False
        assert "measured_tps" not in item["configuration"]


def test_get_unknown_model_returns_404(harness):
    client, _, _ = harness
    response = client.get("/api/models/not-found/inference-configurations")
    assert response.status_code == 404


def test_apply_requires_a_discovered_configuration_and_reuses_callbacks(harness):
    client, applied, recreated = harness
    discovery = client.get("/api/models/demo-model/inference-configurations").json()
    candidate = next(
        item for item in discovery["configurations"]
        if item["configuration"]["speculation"] == "none"
        and item["configuration"]["kv_cache"] == "f16"
        and item["configuration"]["flash_attention"] is True
    )
    response = client.post(
        "/api/models/demo-model/inference-configuration",
        json={
            "configuration_id": candidate["configuration_id"],
            "configuration": candidate["configuration"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "configuration_applied"
    assert body["model_activation"] == "unchanged"
    assert body["benchmark_required"] is True
    assert applied["LLAMA_BATCH_SIZE"] == "1"
    assert applied["LLAMA_ARG_SPEC_TYPE"] == "none"
    assert "LLAMA_ARG_SPEC_DRAFT_N_MAX" not in applied
    assert applied["LLAMA_ARG_CACHE_TYPE_K"] == "f16"
    assert applied["LLAMA_ARG_CACHE_TYPE_V"] == "f16"
    assert "CTX_SIZE" in applied
    assert "MAX_CONTEXT" not in applied
    assert recreated == [["llama-server"]]


def test_apply_rejects_unknown_or_modified_configuration(harness):
    client, applied, recreated = harness
    discovery = client.get("/api/models/demo-model/inference-configurations").json()
    candidate = discovery["configurations"][0]
    changed = dict(candidate["configuration"])
    changed["gpu_layers"] = 999999

    response = client.post(
        "/api/models/demo-model/inference-configuration",
        json={
            "configuration_id": candidate["configuration_id"],
            "configuration": changed,
        },
    )
    assert response.status_code == 409
    assert applied == {}
    assert recreated == []


def test_apply_rejects_configuration_mutated_to_unsupported_runtime(harness):
    client, applied, recreated = harness
    discovery = client.get("/api/models/demo-model/inference-configurations").json()
    candidate = discovery["configurations"][0]
    configuration = dict(candidate["configuration"])
    configuration["runtime"] = "unknown-runtime"
    # The changed configuration cannot be associated with the discovered ID.
    response = client.post(
        "/api/models/demo-model/inference-configuration",
        json={
            "configuration_id": candidate["configuration_id"],
            "configuration": configuration,
        },
    )
    assert response.status_code == 409
    assert applied == {}
    assert recreated == []


def test_unmapped_turbo_and_offload_modes_are_not_discovered(harness):
    client, _, _ = harness
    response = client.get("/api/models/demo-model/inference-configurations")
    assert response.status_code == 200
    for item in response.json()["configurations"]:
        config = item["configuration"]
        assert not str(config.get("kv_cache", "")).startswith("turbo")
        assert config.get("offload") == "none"


def test_mtp_candidates_have_positive_draft_depth(harness):
    client, _, _ = harness
    response = client.get("/api/models/demo-model/inference-configurations")
    assert response.status_code == 200
    mtp = [
        item["configuration"]
        for item in response.json()["configurations"]
        if item["configuration"].get("speculation") == "draft-mtp"
    ]
    assert mtp
    assert all(int(item.get("draft_tokens") or 0) > 0 for item in mtp)

def _client_with_callbacks(apply_environment, recreate_services):
    profile = {
        "runtime": "cafe-llama.cpp",
        "runtime_revision": "test-revision",
        "kernel": "baseline",
        "quantization": "Q4_K_M",
        "context_length": 4096,
        "gpu_layers": 12,
        "kv_cache": "f16",
        "flash_attention": True,
        "offload": "none",
        "speculation": "none",
        "draft_tokens": 0,
        "batch": 1,
    }
    model = {"id": "demo-model", "runtime_profiles": [profile]}
    app = FastAPI()
    app.include_router(create_inference_configuration_router(
        find_model=lambda model_id: model if model_id == "demo-model" else None,
        get_runtime_profiles=lambda item: item.get("runtime_profiles", []),
        apply_environment=apply_environment,
        recreate_services=recreate_services,
        can_apply=lambda: True,
        get_measurements=lambda model_id, workload_id: [],
    ))
    app.dependency_overrides[verify_api_key] = lambda: "test-api-key"
    return TestClient(app)


def _first_valid_candidate(client):
    body = client.get("/api/models/demo-model/inference-configurations").json()
    return next(
        item for item in body["configurations"]
        if item["configuration"]["speculation"] == "none"
        and item["configuration"]["kv_cache"] == "f16"
        and item["configuration"]["flash_attention"] is True
    )


def test_apply_reports_environment_update_failure_without_recreation():
    recreated = []

    def fail_update(_env):
        raise RuntimeError("simulated host-agent outage")

    client = _client_with_callbacks(fail_update, lambda ids: recreated.append(ids) or True)
    candidate = _first_valid_candidate(client)
    response = client.post(
        "/api/models/demo-model/inference-configuration",
        json={"configuration_id": candidate["configuration_id"], "configuration": candidate["configuration"]},
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "environment_update_failed"
    assert recreated == []


def test_apply_reports_partial_state_when_recreation_fails():
    applied = {}

    def save_env(values):
        applied.update(values)
        return {"status": "saved"}

    def fail_recreate(_ids):
        raise RuntimeError("simulated recreate failure")

    client = _client_with_callbacks(save_env, fail_recreate)
    candidate = _first_valid_candidate(client)
    response = client.post(
        "/api/models/demo-model/inference-configuration",
        json={"configuration_id": candidate["configuration_id"], "configuration": candidate["configuration"]},
    )
    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "partial_application"
    assert response.json()["detail"]["environment_update"] == "confirmed"
    assert "CTX_SIZE" in applied



def test_adapter_rejects_unmapped_turbo_and_moe_offload():
    base = {
        "runtime": "cafe-llama.cpp",
        "kernel": "baseline",
        "kv_cache": "f16",
        "flash_attention": True,
        "offload": "none",
        "speculation": "none",
        "draft_tokens": 0,
    }
    turbo = dict(base, kv_cache="turbo4")
    with pytest.raises(ValueError, match="current ODS schema"):
        validate_cafe_configuration(turbo)

    moe = dict(base, offload="host-moe")
    with pytest.raises(ValueError, match="no verified ODS environment mapping"):
        validate_cafe_configuration(moe)
