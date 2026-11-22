"""Dependency-free LEONES reference router and adapter lifecycle."""
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Candidate:
    model_id: str
    hard_fit: bool = True
    evidence_ok: bool = False
    task_fit: bool = False
    llmfit_fit: Optional[float] = None
    observed_tokens_per_second: Optional[float] = None
    openness_score: Optional[float] = None
    runtime_ok: bool = False
    user_score: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def _value(value: Optional[float]) -> float:
    return -1.0 if value is None else float(value)


def rank_candidates(candidates: Iterable[Candidate]) -> List[Candidate]:
    """Rank viable candidates; measured speed outranks llmfit estimates."""
    def key(c: Candidate):
        viable = all((c.hard_fit, c.evidence_ok, c.task_fit, c.runtime_ok))
        measured = _value(c.observed_tokens_per_second)
        return (viable, measured >= 0, measured, _value(c.llmfit_fit),
                _value(c.openness_score), _value(c.user_score))
    return sorted(candidates, key=key, reverse=True)


def select(candidates: Iterable[Candidate]) -> Optional[Candidate]:
    ranked = rank_candidates(candidates)
    return ranked[0] if ranked else None


class Adapter:
    """Common lifecycle for optional LEONES upstream integrations."""
    name = "abstract"

    def probe(self) -> Dict[str, Any]:
        return {"available": False, "adapter": self.name}

    def prepare(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {"plan": plan}

    def run(self, task: Dict[str, Any], prepared_run: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def normalize(self, raw_result: Dict[str, Any]) -> Dict[str, Any]:
        return dict(raw_result)

    def cleanup(self, prepared_run: Dict[str, Any]) -> None:
        return None
