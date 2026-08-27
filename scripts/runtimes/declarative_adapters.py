"""Factory for declarative runtime adapters."""

from __future__ import annotations
from scripts.runtimes.base import RuntimeAdapter


def adapter(runtime_id: str, adapter_id: str) -> RuntimeAdapter:
    return type(
        "DeclarativeRuntimeAdapter",
        (RuntimeAdapter,),
        {"runtime_id": runtime_id, "adapter_id": adapter_id},
    )()
