"""V1.1 TensorRT-LLM adapter."""

from scripts.runtimes.declarative_adapters import adapter

ADAPTER = adapter("TensorRT-LLM", "tensorrt_llm.v1.1")
