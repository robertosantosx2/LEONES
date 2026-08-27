"""Declarative V1.1 target registry entries for future adapters.

This file is deliberately separate from executable adapter registration: a
registry entry does not imply installation or successful execution.
"""
from __future__ import annotations

TARGET_ADAPTERS = {
    "llama.cpp": "llama_cpp.v1",
    "ollama": "ollama.v1",
    "FreeToken": "freetoken.v1",
    "AirLLM": "airllm.v1",
    "vllm": "vllm.v1",
    "sglang": "sglang.v1",
    "mlx": "mlx.v1",
    "mlx-lm": "mlx_lm.v1",
    "exllamav2": "exllamav2.v1",
    "exllamav3": "exllamav3.v1",
    "openvino": "openvino.v1",
    "onnxruntime-genai": "onnxruntime_genai.v1",
    "tensorrt-llm": "tensorrt_llm.v1",
}

IMPLEMENTATION_ORDER = tuple(TARGET_ADAPTERS)
