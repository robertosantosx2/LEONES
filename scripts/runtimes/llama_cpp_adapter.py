#!/usr/bin/env python3
"""Trusted V1.1 adapter for llama.cpp."""
from __future__ import annotations
import re
from typing import Any
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry

TOKENS_PER_SECOND_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE)

class LlamaCppAdapter(RuntimeAdapter):
    runtime_id = "llama.cpp"
    adapter_id = "llama_cpp.v1.1"

    def prepare(self, plan: dict[str, Any], entry: RuntimeEntry) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(self.runtime_id, self.adapter_id, plan["model_id"],
                                    tuple(entry.entrypoint["argv"]),
                                    {"metrics": entry.metrics, "format": plan.get("model_format", "GGUF")})

ADAPTER = LlamaCppAdapter()

def build_command(executable: str, model_path: str, prompt: str, *, context_tokens: int | None = None) -> list[str]:
    """Build a shell-free command; executable must come from the trusted registry."""
    command = [executable, "-m", model_path, "-p", prompt]
    if context_tokens is not None:
        if context_tokens < 1:
            raise ValueError("context_tokens must be positive")
        command.extend(["-c", str(context_tokens)])
    return command

def build_command_from_plan(plan: dict[str, Any], model_path: str, prompt: str, *, context_tokens: int | None = None) -> list[str]:
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not authorized")
    if plan.get("runtime", {}).get("name", plan.get("runtime")) != "llama.cpp":
        raise ValueError("unsupported runtime for llama.cpp adapter")
    if not plan.get("quantization"):
        raise ValueError("runtime plan has no quantization")
    return build_command("llama-cli", model_path, prompt, context_tokens=context_tokens)

def tokens_per_second_pattern() -> str:
    return TOKENS_PER_SECOND_PATTERN.pattern
