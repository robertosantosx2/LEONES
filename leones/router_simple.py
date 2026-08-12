"""Choose one local model from an explicit, small candidate list.

One responsibility: make a transparent first routing decision. It does not
search the internet, download models, execute them, or benchmark them.

The first rule is intentionally simple: prefer a candidate whose capabilities
match the task. If several match, keep their declared order.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Candidate:
    model_id: str
    capabilities: tuple[str, ...] = ()
    backend: str = "llama.cpp"


@dataclass(frozen=True)
class Decision:
    model_id: str
    backend: str
    reason: str


def route(task: str, candidates: list[Candidate]) -> Decision:
    """Return the first candidate matching a simple task keyword."""
    text = task.lower()
    keywords = {
        "coding": ("code", "coding", "python", "program", "script"),
        "reasoning": ("reason", "math", "problem", "analyse", "analyze"),
        "general": (),
    }

    requested = "general"
    for capability, words in keywords.items():
        if any(word in text for word in words):
            requested = capability
            break

    for candidate in candidates:
        if requested == "general" or requested in candidate.capabilities:
            return Decision(candidate.model_id, candidate.backend, f"capability={requested}")

    raise ValueError(f"No candidate available for task capability: {requested}")
