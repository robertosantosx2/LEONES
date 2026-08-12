"""Describe one local LLM without downloading or executing it.

This module has one responsibility: represent model metadata in a small,
portable structure. It deliberately does not inspect remote repositories,
download files, validate licenses, or run inference.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelInfo:
    """Minimal model identity and execution metadata."""

    model_id: str
    family: str | None = None
    revision: str | None = None
    format: str | None = None
    quantization: str | None = None
    size_gb: float | None = None
    capabilities: tuple[str, ...] = ()
    license: str | None = None
    source: str | None = None

    def capabilities_text(self) -> str:
        """Return capabilities as a stable comma-separated value."""
        return ",".join(self.capabilities)
