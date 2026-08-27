"""Trusted V1.1 adapter boundary for Ollama."""
from __future__ import annotations
from typing import Any
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry

ADAPTER_ID = "ollama.v1.1"

class OllamaAdapter(RuntimeAdapter):
    runtime_id = "ollama"
    adapter_id = ADAPTER_ID

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(self.runtime_id, self.adapter_id, plan["model_id"],
                                    tuple(entry.entrypoint["argv"]),
                                    {"protocol": "ollama-api", "metrics": entry.metrics})

ADAPTER = OllamaAdapter()

def prepare(plan: Any) -> RuntimeExecutionSpec:
    """Compatibility wrapper for the pre-V1.1 object-shaped plan."""
    if getattr(plan, "runtime_id", None) != "ollama":
        raise ValueError(f"unsupported runtime for Ollama adapter: {getattr(plan, 'runtime_id', None)!r}")
    if getattr(plan, "adapter_id", None) != ADAPTER_ID:
        raise ValueError(f"unsupported adapter for Ollama: {getattr(plan, 'adapter_id', None)!r}")
    return RuntimeExecutionSpec("ollama", ADAPTER_ID, plan.model_ref, ("ollama",),
                                {"protocol": "ollama-api", "metrics": "api-defined"})
