"""ODS-shaped cafe-llama.cpp runtime adapter contract.

This module is intentionally small: core ICD stays runtime-agnostic while
cafe-llama exposes its known configuration vocabulary and environment mapping.
Execution remains outside runtime_selection.
"""
from __future__ import annotations

from typing import Any

RUNTIME_ID = "cafe-llama.cpp"

UNMAPPED_FUTURE_CAPABILITIES = {
    "kernel": ["ptq1-mmV"],
    "kv_cache": ["turbo2", "turbo3", "turbo4"],
    "offload": ["host-moe", "cpu-moe", "ssd"],
}

CAPABILITIES = {
    # Only expose settings with a known ODS env mapping. ptq1-mmV is a future
    # runtime-build capability until the pinned cafe build exposes a verified selector.
    "kernel": ["baseline"],
    # Match the values documented in ODS .env.example; TurboQuant needs a
    # separate verified adapter for the pinned cafe-llama build.
    "kv_cache": ["f16", "q8_0"],
    "flash_attention": [True, False],
    # ODS currently documents no stable host-MoE/SSD streaming env mapping.
    "offload": ["none"],
    "speculation": ["none", "draft-mtp"],
    "draft_tokens": [0, 1, 2, 4],
}

ENV_MAPPING = {
    "gpu_layers": "LLAMA_ARG_N_GPU_LAYERS",
    "context": "CTX_SIZE",
    "kv_cache": "LLAMA_ARG_CACHE_TYPE_K",
    "flash_attention": "LLAMA_ARG_FLASH_ATTN",
    "speculation": "LLAMA_ARG_SPEC_TYPE",
    "draft_tokens": "LLAMA_ARG_SPEC_DRAFT_N_MAX",
    "batch": "LLAMA_BATCH_SIZE",
}


def validate_cafe_configuration(configuration: dict[str, Any]) -> None:
    if configuration.get("runtime") != RUNTIME_ID:
        raise ValueError("configuration is not a cafe-llama.cpp configuration")

    kernel = str(configuration.get("kernel") or "baseline").lower()
    if kernel not in CAPABILITIES["kernel"]:
        raise ValueError("kernel has no verified ODS environment mapping")
    kv = str(configuration.get("kv_cache") or "").lower()
    if kv not in CAPABILITIES["kv_cache"]:
        raise ValueError("KV cache value is not supported by the current ODS schema")
    offload = str(configuration.get("offload") or "none").lower()
    if offload not in CAPABILITIES["offload"]:
        raise ValueError("offload mode has no verified ODS environment mapping")
    speculation_value = str(configuration.get("speculation") or "none").lower()
    if speculation_value not in CAPABILITIES["speculation"]:
        raise ValueError("speculation mode is not supported by this adapter")
    draft_value = configuration.get("draft_tokens", 0)
    if draft_value not in CAPABILITIES["draft_tokens"]:
        raise ValueError("draft token depth is not supported by this adapter")
    if type(configuration.get("flash_attention")) is not bool:
        raise ValueError("flash_attention must be a boolean")
    if kv.startswith("turbo") and configuration.get("flash_attention") is not True:
        raise ValueError("turbo KV requires flash attention")

    speculation = str(configuration.get("speculation") or "").lower()
    draft_tokens = int(configuration.get("draft_tokens") or 0)
    if speculation in {"none", "off"} and draft_tokens != 0:
        raise ValueError("non-speculative configuration cannot have draft tokens")
    if speculation == "draft-mtp" and draft_tokens <= 0:
        raise ValueError("draft-mtp requires draft tokens")


def configuration_to_env(configuration: dict[str, Any]) -> dict[str, str]:
    validate_cafe_configuration(configuration)
    env: dict[str, str] = {}
    for dimension, key in ENV_MAPPING.items():
        value = configuration.get(dimension)
        if value is None:
            continue
        if dimension == "flash_attention":
            env[key] = "on" if value else "off"
        else:
            env[key] = str(value)
    # This adapter exposes one KV-cache choice for both K and V.
    if configuration.get("kv_cache") is not None:
        env["LLAMA_ARG_CACHE_TYPE_V"] = str(configuration["kv_cache"])

    # ODS schema requires draft depth >= 1. For non-speculative profiles the
    # explicit LLAMA_ARG_SPEC_TYPE=none disables speculation, so do not write
    # a zero draft cap into the environment.
    if str(configuration.get("speculation") or "none").lower() in {"none", "off"}:
        env.pop("LLAMA_ARG_SPEC_DRAFT_N_MAX", None)

    offload = str(configuration.get("offload") or "none").lower()
    if offload != "none":
        raise ValueError("This offload mode has no verified ODS environment mapping yet")
    return env
