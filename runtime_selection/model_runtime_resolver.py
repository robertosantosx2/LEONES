"""Deterministic model -> runtime resolution boundary.

LLMFit returns model candidates, not executable runtime artifacts.  This module
makes that distinction explicit: a model identity may be *resolved* to a
runtime family, but it is not considered installed, available, or measured
until a separate physical preflight proves those facts.

The resolver never installs, downloads, or executes anything.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCHEMA_VERSION = "model-runtime-resolution.v1"


@dataclass(frozen=True)
class Resolution:
    status: str
    model_id: str
    model_format: str | None
    runtime_id: str | None
    runtime_model_ref: str | None
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": self.status,
            "model_id": self.model_id,
            "model_format": self.model_format,
            "runtime_id": self.runtime_id,
            "runtime_model_ref": self.runtime_model_ref,
            "reason": self.reason,
        }


def _infer_format(candidate: dict[str, Any]) -> str | None:
    explicit = candidate.get("model_format")
    if isinstance(explicit, str) and explicit:
        return explicit
    model_id = str(candidate.get("model_id") or candidate.get("model_name") or "")
    lowered = model_id.lower()
    if "gguf" in lowered:
        return "GGUF"
    if any(token in lowered for token in ("awq", "gptq", "fp8", "int8", "int4")):
        return next(
            (token.upper() for token in ("awq", "gptq", "fp8", "int8", "int4") if token in lowered),
            None,
        )
    if "safetensors" in lowered:
        return "safetensors"
    return None


def _normalise_runtime(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    aliases = {
        "llama_cpp": "llama.cpp",
        "llama-cpp": "llama.cpp",
        "ollama": "ollama",
        "vllm": "vLLM",
        "sglang": "SGLang",
    }
    return aliases.get(value, value)


def resolve_model_runtime(
    candidate: dict[str, Any],
    *,
    available_runtimes: set[str] | None = None,
) -> Resolution:
    """Resolve a selected model to a runtime without performing installation.

    Explicit runtime declarations are authoritative.  In particular, a
    Hugging Face/GGUF identifier is never silently converted into an Ollama
    model name.  When no runtime was declared, GGUF deterministically maps to
    llama.cpp because that is the canonical local GGUF runtime in LEONES.
    """
    model_id = str(candidate.get("model_id") or candidate.get("model_name") or "")
    if not model_id:
        return Resolution("BLOCKED", "", None, None, None, "missing model identity")

    model_format = _infer_format(candidate)
    requested_runtime = _normalise_runtime(candidate.get("runtime"))
    runtime_id = requested_runtime

    if runtime_id is None and model_format == "GGUF":
        runtime_id = "llama.cpp"

    if runtime_id is None:
        return Resolution(
            "UNRESOLVED",
            model_id,
            model_format,
            None,
            None,
            "no deterministic runtime mapping for model candidate",
        )

    if available_runtimes is not None and runtime_id not in {
        _normalise_runtime(item) for item in available_runtimes
    }:
        return Resolution(
            "RUNTIME_UNAVAILABLE",
            model_id,
            model_format,
            runtime_id,
            None,
            f"runtime is unavailable: {runtime_id}",
        )

    if runtime_id == "ollama" and model_format not in (None, "Ollama-managed"):
        return Resolution(
            "BLOCKED",
            model_id,
            model_format,
            runtime_id,
            None,
            "Ollama requires an Ollama-managed model reference; refusing to treat a Hugging Face/GGUF id as an Ollama model name",
        )

    runtime_model_ref = model_id if runtime_id == "ollama" and model_format == "Ollama-managed" else None
    return Resolution("RESOLVED", model_id, model_format, runtime_id, runtime_model_ref)
