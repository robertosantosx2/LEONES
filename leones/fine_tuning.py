"""Fine-tuning orchestration boundary for Leones Fine-Tuning."""

from dataclasses import dataclass


@dataclass(frozen=True)
class FineTuningPlan:
    method: str
    base_model: str
    dataset: str
    output_format: str | None = None
    notes: tuple[str, ...] = ()


class FineTuningPlanner:
    """Create explicit, reproducible adaptation plans before execution."""

    SUPPORTED_METHODS = ("lora", "qlora")

    def plan(self, base_model: str, dataset: str, method: str = "qlora") -> FineTuningPlan:
        method = method.lower()
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unsupported initial fine-tuning method: {method}")
        return FineTuningPlan(method=method, base_model=base_model, dataset=dataset)
