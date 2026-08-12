"""Minimal reproducible inference benchmark harness for LEONES."""

from dataclasses import dataclass
from time import perf_counter

from .runtime import RuntimeAdapter


@dataclass(frozen=True)
class InferenceMeasurement:
    first_token_s: float
    total_s: float
    output_tokens: int
    tokens_per_second: float


class InferenceBenchmark:
    def run(self, runtime: RuntimeAdapter, prompt: str, max_tokens: int = 64) -> InferenceMeasurement:
        start = perf_counter()
        first = None
        output = []
        for chunk in runtime.generate(prompt, max_tokens=max_tokens):
            if first is None:
                first = perf_counter()
            output.append(chunk)
        end = perf_counter()
        first = first or end
        total = max(end - start, 1e-9)
        # Exact tokenization belongs to the backend. Until exposed, use a
        # conservative whitespace proxy and label this measurement accordingly.
        tokens = sum(len(part.split()) for part in output)
        return InferenceMeasurement(
            first_token_s=first - start,
            total_s=total,
            output_tokens=tokens,
            tokens_per_second=tokens / total,
        )
