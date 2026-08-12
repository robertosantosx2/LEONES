"""Runtime preparation and model resolution for LEONES 0.2.

The manager deliberately separates *where a model comes from* from *how it runs*.
A future model-registry adapter can implement ModelSource without making the
Runtime depend on a specific desktop application.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .core.contracts import ModelCandidate, RouteDecision
from .runtime import RuntimeAdapter, RuntimeRegistry


class ModelSource(Protocol):
    def resolve(self, model: ModelCandidate) -> Path:
        """Return a local model path, preparing/downloading it if necessary."""
        ...


@dataclass(frozen=True)
class LocalModelSource:
    root: Path

    def resolve(self, model: ModelCandidate) -> Path:
        """Resolve an already-downloaded model using deterministic filenames.

        Downloading is intentionally not implicit yet: autonomous acquisition will
        be added as a separate source adapter with checksum/licence verification.
        """
        candidates = [
            self.root / model.model_id,
            self.root / f"{model.model_id}.gguf",
        ]
        for path in candidates:
            if path.is_file():
                return path
        raise FileNotFoundError(
            f"Model {model.model_id!r} was not found under {self.root}. "
            "Register a ModelSource capable of acquisition for automatic download."
        )


class RuntimeManager:
    """Bind a Router decision to a concrete local runtime adapter."""

    def __init__(self, registry: RuntimeRegistry, source: ModelSource) -> None:
        self.registry = registry
        self.source = source

    def prepare(self, decision: RouteDecision, model: ModelCandidate) -> RouteDecision:
        path = self.source.resolve(model)
        parameters = dict(decision.parameters)
        parameters["model_path"] = str(path)
        return RouteDecision(
            model_id=decision.model_id,
            quantization=decision.quantization,
            backend=decision.backend,
            device=decision.device,
            parameters=parameters,
            rationale=decision.rationale + (f"model_path={path}",),
        )

    def load(self, decision: RouteDecision) -> RuntimeAdapter:
        adapter = self.registry.get(decision.backend)
        if not adapter.available():
            raise RuntimeError(f"Runtime backend unavailable: {decision.backend}")
        adapter.load(decision)
        return adapter
