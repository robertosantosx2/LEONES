"""Trusted adapter boundary for Ollama.

The selection layer remains declarative. This adapter converts an already
validated Ollama selection plan into execution metadata, but never records
benchmark measurements.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ADAPTER_ID = "ollama.v1"


@dataclass(frozen=True)
class OllamaExecutionSpec:
    runtime_id: str
    adapter_id: str
    model_ref: str
    execution_metadata: dict[str, Any]


def prepare(plan: Any) -> OllamaExecutionSpec:
    if plan.runtime_id != "ollama":
        raise ValueError(
            f"unsupported runtime for Ollama adapter: {plan.runtime_id!r}"
        )

    if plan.adapter_id != ADAPTER_ID:
        raise ValueError(
            f"unsupported adapter for Ollama: {plan.adapter_id!r}"
        )

    metadata = {
        "runner": "ollama",
        "protocol": "ollama-api",
    }

    # Deliberately no command/argv/shell and no performance evidence.
    return OllamaExecutionSpec(
        runtime_id=plan.runtime_id,
        adapter_id=plan.adapter_id,
        model_ref=plan.model_ref,
        execution_metadata=metadata,
    )
