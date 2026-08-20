"""Small adapter between llmfit JSON output and the LEONES Router."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Mapping

@dataclass(frozen=True)
class LLMFitCandidate:
    model: str
    llmfit_fit: str | None = None
    llmfit_score: float | None = None
    llmfit_quality_estimate: float | None = None
    llmfit_speed_estimate: float | None = None
    llmfit_context_fit: str | None = None
    llmfit_quantization: str | None = None
    llmfit_run_mode: str | None = None
    llmfit_memory_estimate: float | None = None
    llmfit_runtime: str | None = None
    source: str = "llmfit"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _first(item: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return None

def normalize_candidate(item: Mapping[str, Any]) -> LLMFitCandidate:
    """Normalise common llmfit JSON fields without inventing values."""
    model = _first(item, "model", "name", "model_name", "id")
    if not model:
        raise ValueError("llmfit candidate has no model identifier")
    return LLMFitCandidate(
        model=str(model),
        llmfit_fit=_first(item, "fit", "fit_status"),
        llmfit_score=_first(item, "score"),
        llmfit_quality_estimate=_first(item, "quality", "quality_score"),
        llmfit_speed_estimate=_first(item, "speed", "speed_estimate", "estimated_tps"),
        llmfit_context_fit=_first(item, "context", "context_fit"),
        llmfit_quantization=_first(item, "quantization", "quant", "quantization_name"),
        llmfit_run_mode=_first(item, "run_mode", "mode", "execution_mode"),
        llmfit_memory_estimate=_first(item, "memory", "memory_estimate", "estimated_memory"),
        llmfit_runtime=_first(item, "runtime", "backend"),
    )

def normalize_response(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return normalised candidates from common llmfit wrapper fields."""
    raw = payload.get("models", payload.get("candidates", payload.get("results", [])))
    if not isinstance(raw, list):
        raise ValueError("llmfit response does not contain a candidate list")
    return [normalize_candidate(item).to_dict() for item in raw if isinstance(item, Mapping)]

def attach_provenance(candidates: list[dict[str, Any]], version: str | None) -> list[dict[str, Any]]:
    """Mark external values as estimates and retain source version."""
    return [{**candidate, "llmfit_source_version": version, "estimate_status": "estimated"} for candidate in candidates]
