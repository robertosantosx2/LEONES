from __future__ import annotations

import pytest

from runtime_selection import (
    CAFE_RUNTIME_ID,
    DEFAULT_RUNTIME_ID,
    RuntimeSelectionError,
    resolve_runtime_selection,
)


REGISTRY = {
    DEFAULT_RUNTIME_ID: {
        "id": DEFAULT_RUNTIME_ID,
        "build_id": "ods-pinned-llama-server",
        "source": "ggml-org/llama.cpp",
        "api_compatible": True,
        "api_base_url": "http://llama-server:8080",
        "capabilities": ["chat"],
    },
    CAFE_RUNTIME_ID: {
        "id": CAFE_RUNTIME_ID,
        "build_id": "cafe-0.75-cuda12.4-sha256:verified",
        "source": "quimmedes/cafe-llama.cpp",
        "api_compatible": True,
        "api_base_url": "http://cafe-llama:8081",
        "capabilities": ["chat", "moe-host-offload", "mtp"],
    },
}


def test_absent_selector_preserves_legacy_llama_server_default():
    result = resolve_runtime_selection(
        model_profile={"backend": "nvidia"},
        runtime_registry=REGISTRY,
        installed_runtime_ids={DEFAULT_RUNTIME_ID},
    )
    assert result["runtime_id"] == DEFAULT_RUNTIME_ID
    assert result["api_base_url"] == "http://llama-server:8080"
    assert result["selection_source"] == "default"


def test_explicit_global_cafe_requires_explicit_cafe_model_profile():
    with pytest.raises(RuntimeSelectionError, match="does not explicitly select"):
        resolve_runtime_selection(
            model_profile={"backend": "nvidia", "compatible": True},
            runtime_registry=REGISTRY,
            installed_runtime_ids={DEFAULT_RUNTIME_ID, CAFE_RUNTIME_ID},
            configured_runtime_id=CAFE_RUNTIME_ID,
        )


def test_explicit_cafe_selection_resolves_its_own_endpoint_and_identity():
    result = resolve_runtime_selection(
        model_profile={
            "runtime_id": CAFE_RUNTIME_ID,
            "compatible": True,
            "model_id": "example-moe",
        },
        runtime_registry=REGISTRY,
        installed_runtime_ids={DEFAULT_RUNTIME_ID, CAFE_RUNTIME_ID},
        configured_runtime_id=CAFE_RUNTIME_ID,
    )
    assert result["runtime_id"] == CAFE_RUNTIME_ID
    assert result["api_base_url"] == "http://cafe-llama:8081"
    assert result["build_id"].startswith("cafe-0.75")
    assert result["selection_source"] == "configured"
    assert "mtp" in result["capabilities"]


def test_per_model_selection_takes_precedence_over_global_default():
    result = resolve_runtime_selection(
        model_profile={"runtime_id": CAFE_RUNTIME_ID, "compatible": True},
        runtime_registry=REGISTRY,
        installed_runtime_ids={DEFAULT_RUNTIME_ID, CAFE_RUNTIME_ID},
        model_runtime_id=CAFE_RUNTIME_ID,
        configured_runtime_id=DEFAULT_RUNTIME_ID,
    )
    assert result["runtime_id"] == CAFE_RUNTIME_ID
    assert result["selection_source"] == "model"


def test_unavailable_or_unregistered_runtime_fails_closed():
    with pytest.raises(RuntimeSelectionError, match="not installed"):
        resolve_runtime_selection(
            model_profile={"runtime_id": CAFE_RUNTIME_ID, "compatible": True},
            runtime_registry=REGISTRY,
            installed_runtime_ids={DEFAULT_RUNTIME_ID},
            configured_runtime_id=CAFE_RUNTIME_ID,
        )
    with pytest.raises(RuntimeSelectionError, match="not registered"):
        resolve_runtime_selection(
            model_profile={},
            runtime_registry=REGISTRY,
            installed_runtime_ids={DEFAULT_RUNTIME_ID},
            configured_runtime_id="made-up-runtime",
        )


def test_binary_name_or_missing_build_provenance_is_not_runtime_identity():
    registry = {**REGISTRY, CAFE_RUNTIME_ID: {
        **REGISTRY[CAFE_RUNTIME_ID], "build_id": "", "source": "ggml-org/llama.cpp"
    }}
    with pytest.raises(RuntimeSelectionError, match="build identity"):
        resolve_runtime_selection(
            model_profile={"runtime_id": CAFE_RUNTIME_ID, "compatible": True},
            runtime_registry=registry,
            installed_runtime_ids={DEFAULT_RUNTIME_ID, CAFE_RUNTIME_ID},
            configured_runtime_id=CAFE_RUNTIME_ID,
        )


def test_incompatible_model_profile_fails_closed():
    with pytest.raises(RuntimeSelectionError, match="not compatible"):
        resolve_runtime_selection(
            model_profile={"runtime_id": CAFE_RUNTIME_ID, "compatible": False},
            runtime_registry=REGISTRY,
            installed_runtime_ids={DEFAULT_RUNTIME_ID, CAFE_RUNTIME_ID},
            configured_runtime_id=CAFE_RUNTIME_ID,
        )
