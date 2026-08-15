"""Open LLM Atlas - deterministic Recommendation Engine v0.1.

The engine is intentionally conservative and explainable. It separates:
- hard technical viability;
- workload fit;
- empirical performance;
- quality/capability evidence;
- JGB openness;
- user preferences.

JGB is never treated as model quality. Missing evidence remains unknown.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Hardware:
    name: str
    ram_gb: float
    vram_gb: float = 0.0
    gpu_vendor: Optional[str] = None


@dataclass
class Deployment:
    deployment_id: str
    model_id: str
    estimated_memory_gb: float
    context_tokens: int
    supported_workloads: set[str] = field(default_factory=set)
    supported_hardware: set[str] = field(default_factory=set)
    supported_runtimes: set[str] = field(default_factory=set)
    quality_score: Optional[float] = None
    tokens_per_second: Optional[float] = None
    jgb_level: Optional[int] = None
    jgb_confidence: str = "unknown"
    notes: str = ""


@dataclass
class Request:
    workload: str
    hardware_name: str
    hardware_ram_gb: float
    hardware_vram_gb: float = 0.0
    required_context_tokens: int = 4096
    min_tokens_per_second: Optional[float] = None
    max_memory_gb: Optional[float] = None
    required_jgb_level: Optional[int] = None
    prefer_jgb: bool = False
    local_only: bool = True
    quality_weight: float = 0.35
    speed_weight: float = 0.25
    memory_weight: float = 0.15
    openness_weight: float = 0.10
    compatibility_weight: float = 0.15


@dataclass
class Result:
    deployment_id: str
    model_id: str
    rank: int
    viable: bool
    fit_score: float
    explanation: list[str]
    confidence: str


def _memory_limit(req: Request) -> float:
    # Conservative default: leave headroom for OS/runtime/context/cache.
    # GPU deployments use VRAM plus system RAM; the deployment estimate is
    # interpreted as total required working memory by v0.1.
    if req.max_memory_gb is not None:
        return req.max_memory_gb
    return req.hardware_ram_gb + req.hardware_vram_gb


def recommend(request: Request, deployments: list[Deployment]) -> list[Result]:
    """Return deterministic, explainable recommendations."""
    results: list[Result] = []
    memory_limit = _memory_limit(request)

    for d in deployments:
        reasons: list[str] = []
        viable = True

        if d.estimated_memory_gb > memory_limit:
            viable = False
            reasons.append(
                f"inviable: estimated memory {d.estimated_memory_gb:.1f} GB "
                f"> available limit {memory_limit:.1f} GB"
            )

        if d.context_tokens < request.required_context_tokens:
            viable = False
            reasons.append(
                f"inviable: context {d.context_tokens} < "
                f"required {request.required_context_tokens}"
            )

        if d.supported_workloads and request.workload not in d.supported_workloads:
            viable = False
            reasons.append(f"inviable: workload '{request.workload}' not supported")

        if d.supported_hardware and request.hardware_name not in d.supported_hardware:
            viable = False
            reasons.append(f"inviable: hardware profile not supported")

        if request.required_jgb_level is not None:
            if d.jgb_level is None:
                viable = False
                reasons.append("inviable: required JGB level is unknown")
            elif d.jgb_level < request.required_jgb_level:
                viable = False
                reasons.append(
                    f"inviable: JGB {d.jgb_level} < required {request.required_jgb_level}"
                )

        if request.min_tokens_per_second is not None:
            if d.tokens_per_second is None:
                viable = False
                reasons.append("inviable: required performance is unknown")
            elif d.tokens_per_second < request.min_tokens_per_second:
                viable = False
                reasons.append(
                    f"inviable: {d.tokens_per_second:.1f} tok/s < "
                    f"required {request.min_tokens_per_second:.1f} tok/s"
                )

        if not viable:
            results.append(Result(d.deployment_id, d.model_id, 9999, False, 0.0, reasons, "low"))
            continue

        quality = (d.quality_score or 0.0) / 100.0
        speed = min((d.tokens_per_second or 0.0) / 50.0, 1.0)
        memory = max(0.0, 1.0 - d.estimated_memory_gb / max(memory_limit, 1.0))
        compatibility = 1.0
        openness = (d.jgb_level / 5.0) if d.jgb_level is not None else 0.0

        score = (
            request.quality_weight * quality
            + request.speed_weight * speed
            + request.memory_weight * memory
            + request.compatibility_weight * compatibility
            + (request.openness_weight * openness if request.prefer_jgb else 0.0)
        )

        reasons.extend([
            "viable for the requested hardware/workload constraints",
            f"quality contribution={quality:.2f}",
            f"speed contribution={speed:.2f}",
            f"memory headroom contribution={memory:.2f}",
        ])
        if d.jgb_level is None:
            reasons.append("JGB unknown: no openness assumption was made")
        else:
            reasons.append(
                f"JGB={d.jgb_level} (confidence={d.jgb_confidence}); "
                "JGB is treated as openness, not quality"
            )

        confidence = "high"
        if d.tokens_per_second is None or d.quality_score is None:
            confidence = "medium"
        if d.jgb_level is None or d.jgb_confidence in {"low", "unknown"}:
            confidence = "low" if request.prefer_jgb else confidence

        results.append(Result(d.deployment_id, d.model_id, 0, True, score, reasons, confidence))

    viable_results = sorted(
        [r for r in results if r.viable], key=lambda r: r.fit_score, reverse=True
    )
    for i, r in enumerate(viable_results, 1):
        r.rank = i

    return viable_results + [r for r in results if not r.viable]
