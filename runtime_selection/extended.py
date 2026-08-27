"""V1.1 adapter boundaries for the remaining runtime families.

These adapters intentionally stop at a trusted execution specification. They do
not claim installation, model availability, successful execution, or measured
performance. Those facts belong to the runner and runtime-benchmark.v1.
"""
from __future__ import annotations

from .adapters import ExecutionSpec
from .contract import RuntimeSelectionPlan, validate_plan

ADAPTERS = {
    "Ollama": "ollama.v1",
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


def prepare(plan: RuntimeSelectionPlan) -> ExecutionSpec:
    expected = ADAPTERS.get(plan.runtime_id)
    if expected is None:
        raise ValueError(f"unsupported extended runtime: {plan.runtime_id!r}")
    if plan.adapter_id != expected:
        raise ValueError(f"unexpected adapter for {plan.runtime_id}: {plan.adapter_id!r}")
    validate_plan(plan.to_dict())
    return ExecutionSpec(
        runtime_id=plan.runtime_id,
        adapter_id=expected,
        model_ref=plan.model_ref,
        execution_metadata={"prepared": True, "runner": plan.runtime_id},
    )
