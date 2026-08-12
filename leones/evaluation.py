"""Benchmark and evaluation contracts."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    description: str
    agentic: bool = True


LOTB_CASES = (
    EvaluationCase("B01", "memoria/localidad"),
    EvaluationCase("B02", "operación sobre archivos"),
    EvaluationCase("B03", "tarea multietapa"),
    EvaluationCase("B04", "recuperación ante fallo"),
    EvaluationCase("B05", "coding local"),
)


@dataclass(frozen=True)
class EvaluationResult:
    case_id: str
    success: bool
    duration_s: float | None = None
    error: str | None = None
    evidence_status: str = "reported"
