"""V1.1 vLLM adapter."""

from scripts.runtimes.declarative_adapters import adapter

ADAPTER = adapter("vLLM", "vllm.v1.1")
