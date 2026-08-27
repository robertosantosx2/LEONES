"""Runtime registry and capability matching for V1.1."""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping
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
        model, hw, workload = request.model, request.hardware, request.workload
        architecture = self._supports(self.supported_architectures, model.get("architecture"))
        model_format = self._supports(self.supported_model_formats, model.get("format"))
        quantization = self._supports(self.supported_quantizations, model.get("quantization"))
        requested_hardware = set(hw.get("accelerators") or [])
        hardware = not self.hardware or bool(requested_hardware & set(self.hardware))
        available_memory = hw.get("memory_gb")
        memory = self.min_memory_gb is None or (isinstance(available_memory, (int, float)) and available_memory >= self.min_memory_gb)
        requested_context = workload.get("context_length")
        context = self.max_context is None or not isinstance(requested_context, (int, float)) or requested_context <= self.max_context
        mode = workload.get("execution_mode")
        workload_ok = not self.execution_modes or not mode or mode in self.execution_modes
        return CapabilityMatch(architecture, model_format, quantization, hardware, memory, context, workload_ok)

    @staticmethod
    def _supports(supported: frozenset[str], requested: Any) -> bool:
        return not supported or not requested or str(requested) in supported

class RuntimeRegistry:
    def __init__(self, runtimes: Iterable[RuntimeDescriptor] = ()) -> None:
        self._runtimes: dict[str, RuntimeDescriptor] = {}
        for runtime in runtimes: self.register(runtime)
    def register(self, runtime: RuntimeDescriptor) -> None:
        if runtime.runtime_id in self._runtimes: raise ValueError(f"runtime already registered: {runtime.runtime_id}")
        self._runtimes[runtime.runtime_id] = runtime
    def get(self, runtime_id: str) -> RuntimeDescriptor: return self._runtimes[runtime_id]
    def all(self) -> tuple[RuntimeDescriptor, ...]: return tuple(self._runtimes.values())
    def match(self, request: RuntimeSelectionRequest) -> list[tuple[RuntimeDescriptor, CapabilityMatch]]:
        return [(runtime, runtime.match(request)) for runtime in self._runtimes.values() if runtime.enabled and runtime.match(request).compatible]


def _v11_adapter_id(value: str) -> str:
    """Normalize legacy adapter identifiers to the common V1.1 namespace."""
    if value.endswith(".v1.1"): return value
    if value.endswith(".v1"): return value + ".1"
    return value + ".v1.1"


def load_v1_1_registry(path: str | Path | None = None) -> RuntimeRegistry:
    registry_path = Path(path) if path else Path(__file__).with_name("v1_1") / "runtime_registry.json"
    with registry_path.open(encoding="utf-8") as handle: document: Mapping[str, Any] = json.load(handle)
    if document.get("contract") != "runtime-registry.v1.1": raise ValueError("unsupported runtime registry contract")
    runtimes: list[RuntimeDescriptor] = []
    for entry in document.get("runtimes", []):
        hardware = entry.get("hardware", {}); memory = hardware.get("memory", {})
        runtimes.append(RuntimeDescriptor(
            runtime_id=str(entry["runtime_id"]), adapter_id=_v11_adapter_id(str(entry["adapter_id"])),
            supported_architectures=frozenset(entry.get("architectures", [])), supported_model_formats=frozenset(entry.get("formats", [])),
            supported_quantizations=frozenset(entry.get("quantizations", [])), hardware=frozenset(hardware.get("accelerators", [])),
            execution_modes=frozenset(entry.get("execution_modes", [])), min_memory_gb=memory.get("minimum_gb"),
            metadata={"display_name": entry.get("display_name"), "entrypoint_ref": entry.get("entrypoint_ref"),
                      "availability": entry.get("availability"), "capabilities": entry.get("capabilities", {}),
                      "metrics": entry.get("metrics", {}), "measurement_policy": entry.get("measurement_policy", {}),
                      "eligibility_gate": entry.get("eligibility_gate"), "version_policy": entry.get("version_policy", {})},
        ))
    return RuntimeRegistry(runtimes)

def build_default_registry() -> RuntimeRegistry:
    return load_v1_1_registry()
