"""V1.1 concrete adapter registry.

Each adapter is intentionally thin: capability decisions stay declarative in
the runtime registry and execution evidence stays in the common benchmark
bridge.
"""
from __future__ import annotations

from scripts.runtimes.base import RuntimeAdapter
from scripts.runtimes.freetoken_adapter import FreeTokenAdapter


class NamedAdapter(RuntimeAdapter):
    def __init__(self, runtime_id: str, adapter_id: str):
        self.runtime_id = runtime_id
        self.adapter_id = adapter_id


ADAPTERS: dict[str, RuntimeAdapter] = {
    "llama.cpp": NamedAdapter("llama.cpp", "llama_cpp.v1.1"),
    "FreeToken": FreeTokenAdapter(),
    "AirLLM": NamedAdapter("AirLLM", "airllm.v1.1"),
    "Ollama": NamedAdapter("Ollama", "ollama.v1.1"),
    "vLLM": NamedAdapter("vLLM", "vllm.v1.1"),
    "SGLang": NamedAdapter("SGLang", "sglang.v1.1"),
    "MLX/MLX-LM": NamedAdapter("MLX/MLX-LM", "mlx.v1.1"),
    "ExLlama": NamedAdapter("ExLlama", "exllama.v1.1"),
    "OpenVINO": NamedAdapter("OpenVINO", "openvino.v1.1"),
    "ONNX Runtime GenAI": NamedAdapter("ONNX Runtime GenAI", "onnxruntime_genai.v1.1"),
    "TensorRT-LLM": NamedAdapter("TensorRT-LLM", "tensorrt_llm.v1.1"),
}


def get_adapter(runtime_id: str) -> RuntimeAdapter:
    try:
        return ADAPTERS[runtime_id]
    except KeyError as exc:
        raise ValueError(f"no trusted adapter registered for runtime: {runtime_id}") from exc
