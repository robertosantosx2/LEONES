"""Runtime abstraction: no desktop application is a LEONES dependency."""

from abc import ABC, abstractmethod
from typing import Any, Iterator

from .core.contracts import RouteDecision


class RuntimeAdapter(ABC):
    """Contract implemented by local inference backends."""

    name: str

    @abstractmethod
    def available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def load(self, decision: RouteDecision) -> None:
        raise NotImplementedError

    @abstractmethod
    def generate(self, prompt: str, **kwargs: Any) -> Iterator[str]:
        raise NotImplementedError

    @abstractmethod
    def unload(self) -> None:
        raise NotImplementedError


class RuntimeRegistry:
    """Registry for interchangeable local runtime adapters."""

    def __init__(self) -> None:
        self._adapters: dict[str, RuntimeAdapter] = {}

    def register(self, adapter: RuntimeAdapter) -> None:
        self._adapters[adapter.name] = adapter

    def get(self, name: str) -> RuntimeAdapter:
        try:
            return self._adapters[name]
        except KeyError as exc:
            raise KeyError(f"Runtime not registered: {name}") from exc

    def available(self) -> list[str]:
        return [name for name, adapter in self._adapters.items() if adapter.available()]
