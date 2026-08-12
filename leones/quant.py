"""Quantization contracts for Leones Quant."""

from dataclasses import dataclass


@dataclass(frozen=True)
class QuantizationCandidate:
    method: str
    format: str
    bits: float
    estimated_size_gb: float | None = None


@dataclass(frozen=True)
class QuantizationAssessment:
    candidate: QuantizationCandidate
    quality_score: float | None = None
    speed_score: float | None = None
    memory_score: float | None = None
    notes: tuple[str, ...] = ()


class LeonesQuant:
    """Decision surface for quantization; actual quantizers plug in later."""

    def rank(self, assessments: list[QuantizationAssessment]) -> list[QuantizationAssessment]:
        return sorted(
            assessments,
            key=lambda item: (
                item.quality_score or 0,
                item.speed_score or 0,
                item.memory_score or 0,
            ),
            reverse=True,
        )
