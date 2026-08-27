"""Compatibility facade over the common V1.1 runtime adapter registry."""
from __future__ import annotations
from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTERS = {
    "ollama": "ollama.v1.1", "vllm": "vllm.v1.1", "sglang": "sglang.v1.1", "mlx": "mlx.v1.1",
    "mlx-lm": "mlx.v1.1", "exllamav2": "exllama.v1.1", "exllamav3": "exllama.v1.1",
    "openvino": "openvino.v1.1", "onnxruntime-genai": "onnxruntime_genai.v1.1", "tensorrt-llm": "tensorrt_llm.v1.1",
}

def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    expected = ADAPTERS.get(plan.runtime_id)
    if expected is None: raise ValueError(f"unsupported extended runtime: {plan.runtime_id!r}")
    if plan.adapter_id != expected: raise ValueError(f"unexpected adapter for {plan.runtime_id}: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(runtime_id=plan.runtime_id, adapter_id=expected, model_ref=plan.model_ref,
                         execution_metadata={"prepared": True, "runner": plan.runtime_id})
