#!/usr/bin/env python3
"""Trusted V1.1 adapter for llama.cpp."""

from __future__ import annotations
import re
from typing import Any
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry

TOKENS_PER_SECOND_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE)
DEFAULT_MAX_OUTPUT_TOKENS = 128


class LlamaCppAdapter(RuntimeAdapter):
    runtime_id = "llama.cpp"
    adapter_id = "llama_cpp.v1.1"

    def prepare(
        self, plan: dict[str, Any], entry: RuntimeEntry
    ) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        return RuntimeExecutionSpec(
            self.runtime_id,
            self.adapter_id,
            plan["model_id"],
            tuple(entry.entrypoint["argv"]),
            {"metrics": entry.metrics, "format": plan.get("model_format", "GGUF")},
        )


ADAPTER = LlamaCppAdapter()


def build_command(
    executable: str,
    model_path: str,
    prompt: str,
    *,
    context_tokens: int | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> list[str]:
    # llama-cli remains interactive after a predefined prompt unless simple IO is
    # requested. A bounded prediction count is also required so benchmark runs
    # terminate deterministically instead of using llama-cli's unlimited default.
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")
    command = [executable, "-m", model_path, "-p", prompt, "--simple-io"]
    if context_tokens is not None:
        if context_tokens < 1:
            raise ValueError("context_tokens must be positive")
        command.extend(["-c", str(context_tokens)])
    command.extend(["-n", str(max_output_tokens)])
    return command


def build_command_from_plan(
    plan: dict[str, Any],
    model_path: str,
    prompt: str,
    *,
    executable: str = "llama-cli",
    context_tokens: int | None = None,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
) -> list[str]:
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not authorized")
    runtime_value = plan.get("runtime")
    runtime_id = (
        runtime_value.get("name") if isinstance(runtime_value, dict) else runtime_value
    )
    if runtime_id != "llama.cpp":
        raise ValueError("unsupported runtime for llama.cpp adapter")
    if executable != "llama-cli":
        raise ValueError("executable is not the trusted llama.cpp registry entrypoint")
    if not plan.get("quantization"):
        raise ValueError("runtime plan has no quantization")
    return build_command(
        executable,
        model_path,
        prompt,
        context_tokens=context_tokens,
        max_output_tokens=max_output_tokens,
    )


def tokens_per_second_pattern() -> str:
    return TOKENS_PER_SECOND_PATTERN.pattern
