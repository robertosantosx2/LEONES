"""Fail-closed runtime selection contract for the staged ODS ICD integration.

This module deliberately separates hardware/model compatibility from runtime
identity. It does not start processes or mutate ODS environment state.
"""
from __future__ import annotations

from typing import Any

DEFAULT_RUNTIME_ID = "llama-server"
CAFE_RUNTIME_ID = "cafe-llama.cpp"
RUNTIME_SELECTOR_ENV = "ODS_INFERENCE_RUNTIME"


class RuntimeSelectionError(ValueError):
    """The requested inference runtime cannot be resolved safely."""


def resolve_runtime_selection(
    *,
    model_profile: dict[str, Any] | None,
    runtime_registry: dict[str, dict[str, Any]],
    installed_runtime_ids: set[str],
    model_runtime_id: str | None = None,
    configured_runtime_id: str | None = None,
    default_runtime_id: str = DEFAULT_RUNTIME_ID,
) -> dict[str, Any]:
    """Resolve the selected provider without guessing from hardware or binary name.

    Precedence is explicit per-model selection, explicit global selection, then
    the established default. Cafe must have a dedicated, compatible profile
    and a registered build identity. Legacy generic profiles remain valid for
    the baseline only; they are never promoted to cafe.
    """
    requested = (
        (model_runtime_id or "").strip()
        or (configured_runtime_id or "").strip()
        or default_runtime_id
    )
    if requested not in runtime_registry:
        raise RuntimeSelectionError(f"Runtime is not registered: {requested}")
    if requested not in installed_runtime_ids:
        raise RuntimeSelectionError(f"Runtime is not installed: {requested}")

    runtime = runtime_registry[requested]
    if runtime.get("id") != requested:
        raise RuntimeSelectionError("Runtime registry identity mismatch")
    if not runtime.get("api_compatible", False):
        raise RuntimeSelectionError(f"Runtime does not satisfy the ODS API contract: {requested}")

    if requested == CAFE_RUNTIME_ID:
        # A name such as llama-server or a GPU backend is not proof of the fork.
        build_id = runtime.get("build_id")
        source = runtime.get("source")
        if not isinstance(build_id, str) or not build_id.strip():
            raise RuntimeSelectionError("Cafe runtime has no verified build identity")
        if source != "quimmedes/cafe-llama.cpp":
            raise RuntimeSelectionError("Runtime build provenance is not cafe-llama.cpp")
        if not isinstance(model_profile, dict):
            raise RuntimeSelectionError("No model compatibility profile is available")
        if model_profile.get("runtime_id") != CAFE_RUNTIME_ID:
            raise RuntimeSelectionError("Model profile does not explicitly select cafe-llama.cpp")
        if model_profile.get("compatible") is not True:
            raise RuntimeSelectionError("Model profile is not compatible with cafe-llama.cpp")
    elif requested == DEFAULT_RUNTIME_ID:
        # Existing ODS profiles may predate explicit runtime_id fields. Preserve
        # that baseline compatibility without extending it to optional runtimes.
        if isinstance(model_profile, dict):
            profile_runtime = model_profile.get("runtime_id")
            if profile_runtime not in (None, "", DEFAULT_RUNTIME_ID):
                raise RuntimeSelectionError("Model profile selects a different runtime")
            if model_profile.get("compatible") is False:
                raise RuntimeSelectionError("Model profile is incompatible with llama-server")
    else:
        if not isinstance(model_profile, dict):
            raise RuntimeSelectionError("No model compatibility profile is available")
        compatible = model_profile.get("compatible_runtimes", [])
        if model_profile.get("runtime_id") != requested and requested not in compatible:
            raise RuntimeSelectionError("Model profile does not declare this runtime compatible")
        if model_profile.get("compatible") is False:
            raise RuntimeSelectionError(f"Model profile is incompatible with {requested}")

    endpoint = runtime.get("api_base_url")
    if not isinstance(endpoint, str) or not endpoint.startswith(("http://", "https://")):
        raise RuntimeSelectionError(f"Runtime has no valid API endpoint: {requested}")

    return {
        "runtime_id": requested,
        "build_id": runtime.get("build_id", "ods-baseline"),
        "api_base_url": endpoint.rstrip("/"),
        "selection_source": (
            "model" if (model_runtime_id or "").strip()
            else "configured" if (configured_runtime_id or "").strip()
            else "default"
        ),
        "capabilities": sorted(
            str(item) for item in runtime.get("capabilities", [])
        ),
    }
