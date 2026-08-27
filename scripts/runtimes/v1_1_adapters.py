"""Canonical V1.1 trusted adapter registry."""
from __future__ import annotations
from scripts.runtimes.llama_cpp_adapter import ADAPTER as LLAMA_CPP
from scripts.runtimes.ollama_adapter import ADAPTER as OLLAMA
from scripts.runtimes.freetoken_adapter import ADAPTER as FREETOKEN
from scripts.runtimes.airllm_adapter import ADAPTER as AIRLLM
from scripts.runtimes.vllm_adapter import ADAPTER as VLLM
from scripts.runtimes.sglang_adapter import ADAPTER as SGLANG
from scripts.runtimes.mlx_adapter import ADAPTER as MLX
from scripts.runtimes.exllama_adapter import ADAPTER as EXLLAMA
from scripts.runtimes.openvino_adapter import ADAPTER as OPENVINO
from scripts.runtimes.onnxruntime_genai_adapter import ADAPTER as ONNXRT_GENAI
from scripts.runtimes.tensorrt_llm_adapter import ADAPTER as TRTLLM

ADAPTERS = {
    "llama.cpp": LLAMA_CPP,
    "FreeToken": FREETOKEN,
    "AirLLM": AIRLLM,
    "Ollama": OLLAMA,
    "vLLM": VLLM,
    "SGLang": SGLANG,
    "MLX/MLX-LM": MLX,
    "ExLlama": EXLLAMA,
    "OpenVINO": OPENVINO,
    "ONNX Runtime GenAI": ONNXRT_GENAI,
    "TensorRT-LLM": TRTLLM,
}

def get_adapter(runtime_id: str):
    try:
        return ADAPTERS[runtime_id]
    except KeyError as exc:
        raise ValueError(f"no trusted adapter registered for runtime: {runtime_id}") from exc
