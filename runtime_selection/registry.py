"""Runtime registry and capability matching for V1.1."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .contract import CapabilityMatch, RuntimeSelectionRequest


@dataclass(frozen=True)
class RuntimeDescriptor:
    runtime_id: str
    adapter_id: str
    supported_architectures: frozenset[str] = frozenset()
    supported_model_formats: frozenset[str] = frozenset()
    supported_quantizations: frozenset[str] = frozenset()
    hardware: frozenset[str] = frozenset()
    execution_modes: frozenset[str] = frozenset()
    max_context: int | None = None
    min_memory_gb: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def match(self, request: RuntimeSelectionRequest) -> CapabilityMatch:
        model = request.model
        hw = request.hardware
        workload = request.workload

        architecture = self._supports(self.supported_architectures, model.get("architecture"))
        model_format = self._supports(self.supported_model_formats, model.get("format"))
        quantization = self._supports(self.supported_quantizations, model.get("quantization"))

        requested_hardware = set(hw.get("accelerators") or [])
        hardware = not self.hardware or bool(requested_hardware & set(self.hardware))

        available_memory = hw.get("memory_gb")
        memory = self.min_memory_gb is None or (
            isinstance(available_memory, (int, float)) and available_memory >= self.min_memory_gb
        )

        requested_context = workload.get("context_length")
        context = self.max_context is None or not isinstance(requested_context, (int, float)) or requested_context <= self.max_context

        mode = workload.get("execution_mode")
        workload_ok = not self.execution_modes or not mode or mode in self.execution_modes

        return CapabilityMatch(architecture, model_format, quantization, hardware,
                               memory, context, workload_ok)

    @staticmethod
    def _supports(supported: frozenset[str], requested: Any) -> bool:
        return not supported or not requested or str(requested) in supported


class RuntimeRegistry:
    def __init__(self, runtimes: Iterable[RuntimeDescriptor] = ()) -> None:
        self._runtimes: dict[str, RuntimeDescriptor] = {}
        for runtime in runtimes:
            self.register(runtime)

    def register(self, runtime: RuntimeDescriptor) -> None:
        if runtime.runtime_id in self._runtimes:
            raise ValueError(f"runtime already registered: {runtime.runtime_id}")
        self._runtimes[runtime.runtime_id] = runtime

    def get(self, runtime_id: str) -> RuntimeDescriptor:
        return self._runtimes[runtime_id]

    def all(self) -> tuple[RuntimeDescriptor, ...]:
        return tuple(self._runtimes.values())

    def match(self, request: RuntimeSelectionRequest) -> list[tuple[RuntimeDescriptor, CapabilityMatch]]:
        return [
            (runtime, runtime.match(request))
            for runtime in self._runtimes.values()
            if runtime.enabled and runtime.match(request).compatible
        ]


def build_default_registry() -> RuntimeRegistry:
    """Initial V1.1 registry: declarations only; adapters are added in order."""
    return RuntimeRegistry([
        RuntimeDescriptor(
            runtime_id="llama.cpp", adapter_id="llama_cpp.v1",
            supported_model_formats=frozenset({"gguf"}),
            supported_quantizations=frozenset({"q2", "q3", "q4", "q5", "q6", "q8", "f16", "f32"}),
            hardware=frozenset({"cpu", "cuda", "metal", "vulkan", "sycl"}),
        ),
        RuntimeDescriptor(
            runtime_id="ollama", adapter_id="ollama.v1",
            hardware=frozenset({"cpu", "cuda", "metal", "rocm"}),
        ),
        RuntimeDescriptor(
            runtime_id="FreeToken", adapter_id="freetoken.v1",
            hardware=frozenset({"cuda"}), metadata={"requires_gate": True},
        ),
        RuntimeDescriptor(
            runtime_id="AirLLM", adapter_id="airllm.v1",
            hardware=frozenset({"cpu", "cuda"}),
        ),
    ])
