"""V1.1 ONNX Runtime GenAI adapter."""

from scripts.runtimes.declarative_adapters import adapter

ADAPTER = adapter("ONNX Runtime GenAI", "onnxruntime_genai.v1.1")
