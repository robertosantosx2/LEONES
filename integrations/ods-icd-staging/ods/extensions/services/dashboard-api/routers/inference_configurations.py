"""Staged ODS Dashboard API router for Inference Configuration Discovery.

This module is a transfer-ready implementation proposal. ODS must wire it into
its FastAPI app with callbacks bound to the existing model lookup, host-agent
environment update, and runtime lifecycle helpers. It deliberately does not
write .env or load/activate models itself.
"""
from __future__ import annotations

import inspect
from typing import Any, Callable, Iterable

from fastapi import APIRouter, Body, Depends, HTTPException
from fastapi.responses import JSONResponse

from cafe_llama_icd import (
    CAPABILITIES as CAFE_CAPABILITIES,
    RUNTIME_ID as CAFE_RUNTIME_ID,
    configuration_to_env as cafe_configuration_to_env,
    validate_cafe_configuration,
)
from inference_configuration import (
    ConfigurationCandidate,
    configuration_signature,
    discover_configurations,
    validate_configuration,
)
from security import verify_api_key


def create_inference_configuration_router(
    *,
    find_model: Callable[[str], dict[str, Any] | None],
    get_runtime_profiles: Callable[[dict[str, Any]], Iterable[dict[str, Any]]],
    apply_environment: Callable[[dict[str, str]], Any],
    recreate_services: Callable[[list[str]], Any],
    can_apply: Callable[[], bool] = lambda: True,
) -> APIRouter:
    """Build ICD routes around existing ODS lifecycle functions.

    `apply_environment` must delegate to the existing host-agent environment
    update path. `recreate_services` must delegate to the existing targeted
    service lifecycle path. Both callbacks may be sync or async.
    """
    router = APIRouter(tags=["models"])

    def _model_or_404(model_id: str) -> dict[str, Any]:
        model = find_model(model_id)
        if not isinstance(model, dict):
            raise HTTPException(
                status_code=404,
                detail=f"Model '{model_id}' not found in library or local GGUF files",
            )
        return model

    def _discover(model: dict[str, Any]) -> list[ConfigurationCandidate]:
        profiles = list(get_runtime_profiles(model) or [])
        candidates: list[ConfigurationCandidate] = []
        for profile in profiles:
            runtime = (
                profile.get("runtime")
                or profile.get("runtime_id")
                or profile.get("backend")
            )
            capabilities = CAFE_CAPABILITIES if runtime == CAFE_RUNTIME_ID else None
            try:
                discovered = discover_configurations(
                    model=model,
                    runtime_profiles=[profile],
                    capabilities=capabilities,
                )
                if runtime == CAFE_RUNTIME_ID:
                    # Capability products include combinations that are
                    # individually supported but invalid together. Filter
                    # those before exposing them to the Dashboard.
                    compatible = []
                    for candidate in discovered:
                        try:
                            validate_cafe_configuration(candidate.configuration)
                        except (TypeError, ValueError):
                            continue
                        compatible.append(candidate)
                    discovered = compatible
                candidates.extend(discovered)
            except (TypeError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        # Stable order and exact signature deduplication are provided by the
        # core. Keep the response deterministic even across profile sources.
        unique: dict[str, ConfigurationCandidate] = {}
        for candidate in candidates:
            unique.setdefault(candidate.configuration_id, candidate)
        return list(unique.values())

    @router.get("/api/models/{model_id}/inference-configurations")
    def list_inference_configurations(
        model_id: str,
        api_key: str = Depends(verify_api_key),
    ) -> JSONResponse:
        model = _model_or_404(model_id)
        candidates = _discover(model)
        return JSONResponse({
            "schema_version": "inference-configuration-discovery.v1",
            "model_id": model_id,
            "configurations": [candidate.to_dict() for candidate in candidates],
            "measurement_required": True,
            "execution_authorized": False,
        }, headers={"Cache-Control": "no-store"})

    @router.post("/api/models/{model_id}/inference-configuration")
    async def apply_inference_configuration(
        model_id: str,
        body: dict[str, Any] = Body(...),
        api_key: str = Depends(verify_api_key),
    ) -> JSONResponse:
        model = _model_or_404(model_id)
        if not can_apply():
            raise HTTPException(
                status_code=409,
                detail="This ODS installation cannot change the selected runtime right now",
            )
        configuration_id = body.get("configuration_id")
        configuration = body.get("configuration")
        if not isinstance(configuration_id, str) or not configuration_id:
            raise HTTPException(status_code=400, detail="configuration_id is required")
        if not isinstance(configuration, dict):
            raise HTTPException(status_code=400, detail="configuration must be an object")
        try:
            validate_configuration(configuration)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        candidates = _discover(model)
        matched = next(
            (
                candidate for candidate in candidates
                if candidate.configuration_id == configuration_id
                and configuration_signature(configuration) == configuration_id
            ),
            None,
        )
        if matched is None:
            raise HTTPException(
                status_code=409,
                detail="Configuration is stale, unsupported, or does not belong to this model/runtime profile",
            )

        runtime = configuration.get("runtime")
        if runtime != CAFE_RUNTIME_ID:
            raise HTTPException(
                status_code=409,
                detail=f"Runtime '{runtime}' has no configuration application adapter yet",
            )
        try:
            validate_cafe_configuration(configuration)
            env = cafe_configuration_to_env(configuration)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        # Do not persist environment values here. ODS must supply callbacks
        # backed by its host-agent update and lifecycle code paths.
        try:
            update_result = apply_environment(env)
            if inspect.isawaitable(update_result):
                update_result = await update_result
            recreate_result = recreate_services(["llama-server"])
            if inspect.isawaitable(recreate_result):
                recreate_result = await recreate_result
        except Exception as exc:
            # Report failure without exposing callback internals or secrets.
            raise HTTPException(
                status_code=502,
                detail="ODS could not confirm application of the inference configuration; refresh runtime status",
            ) from exc

        return JSONResponse({
            "status": "configuration_applied",
            "model_id": model_id,
            "configuration_id": configuration_id,
            "runtime": runtime,
            "environment_keys": sorted(env),
            "environment_update": "confirmed" if update_result is not False else "unknown",
            "service_recreation": "confirmed" if recreate_result is not False else "unknown",
            "model_activation": "unchanged",
            "benchmark_required": True,
            "explicit_user_apply": True,
        }, headers={"Cache-Control": "no-store"})

    return router
