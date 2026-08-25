"""Adapter for the public CanIRun.ai compatibility/recommendation API.

CanIRun is an external estimator. Values produced here are explicitly marked
as estimates and are never promoted to measured performance or LEONES scores.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import json

API_BASE = "https://canirun.ai/api"


@dataclass(frozen=True)
class CanIRunCandidate:
    model_id: str
    model_name: str | None
    quantization: str | None
    fit: str
    grade: str | None
    score: float | None
    estimated_tps: float | None
    estimated_memory_gb: float | None
    memory_headroom_gb: float | None
    recommended_quantization: str | None
    source: str = "canirun"
    estimate_status: str = "estimated"
    measured_tps: float | None = None
    measurement_status: str = "not-measured"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _first(item: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None


def _estimated(item: Mapping[str, Any], *keys: str) -> Any:
    nested = item.get("estimated")
    if isinstance(nested, Mapping):
        value = _first(nested, *keys)
        if value is not None:
            return value
    return _first(item, *keys)


def normalize_compatibility(payload: Mapping[str, Any]) -> CanIRunCandidate:
    """Normalize one /api/compatibility response without inventing values."""
    model_id = _first(payload, "modelId", "model_id", "id")
    if not model_id:
        raise ValueError("CanIRun response has no model identifier")

    status = str(_first(payload, "status", "fit") or "unknown")
    return CanIRunCandidate(
        model_id=str(model_id),
        model_name=_first(payload, "modelName", "name"),
        quantization=_first(payload, "quantization", "quant"),
        fit=status,
        grade=_first(payload, "grade"),
        score=_first(payload, "score"),
        estimated_tps=_estimated(payload, "tokensPerSecond", "estimatedTokensPerSecond"),
        estimated_memory_gb=_estimated(payload, "vramRequiredGb", "ramRequiredGb", "modelSizeGb"),
        memory_headroom_gb=_estimated(payload, "memoryHeadroomGb"),
        recommended_quantization=_first(payload, "recommendedQuantization"),
    )


def normalize_recommendations(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize /api/recommend while preserving CanIRun's ranking signals."""
    raw = payload.get("recommendations", [])
    if not isinstance(raw, list):
        raise ValueError("CanIRun response does not contain recommendations")
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        model_id = _first(item, "modelId", "model_id", "id")
        if not model_id:
            continue
        result.append(
            CanIRunCandidate(
                model_id=str(model_id),
                model_name=_first(item, "name", "modelName"),
                quantization=_first(item, "quantization"),
                fit=str(_first(item, "status", "fit") or "unknown"),
                grade=_first(item, "grade"),
                score=_first(item, "score"),
                estimated_tps=_first(item, "estimatedTokensPerSecond", "estimated_tps"),
                estimated_memory_gb=_first(item, "vramRequiredGb", "diskSizeGb", "estimated_memory_gb"),
                memory_headroom_gb=None,
                recommended_quantization=None,
            ).to_dict()
        )
    return result


def build_hardware(*, ram_gb: float, gpu_name: str | None = None,
                   vram_gb: float | None = None,
                   memory_bandwidth_gbps: float | None = None,
                   cpu_name: str | None = None) -> dict[str, Any]:
    hardware: dict[str, Any] = {"ramGb": ram_gb}
    if cpu_name:
        hardware["cpu"] = {"name": cpu_name}
    if gpu_name or vram_gb is not None or memory_bandwidth_gbps is not None:
        hardware["gpu"] = {
            "name": gpu_name,
            "vramGb": vram_gb,
            "memoryBandwidthGbps": memory_bandwidth_gbps,
        }
    return hardware


def compatibility_request(model_id: str, hardware: Mapping[str, Any],
                           quantization: str | None = None,
                           *, base_url: str = API_BASE, timeout: float = 15.0) -> CanIRunCandidate:
    payload: dict[str, Any] = {"hardware": dict(hardware), "modelId": model_id}
    if quantization is not None:
        payload["quantization"] = quantization
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{base_url.rstrip('/')}/compatibility",
        data=body,
        headers={"content-type": "application/json", "accept": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            decoded = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"CanIRun API unavailable: {exc}") from exc
    if not isinstance(decoded, Mapping):
        raise ValueError("CanIRun API returned a non-object response")
    return normalize_compatibility(decoded)
