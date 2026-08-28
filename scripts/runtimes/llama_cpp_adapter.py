#!/usr/bin/env python3
"""Translate an authorized LEONES plan into a llama.cpp invocation.

This module is deliberately thin. LEONES owns selection and evidence policy;
llama.cpp remains the external inference runtime. The adapter only validates
the runtime-specific part of an already authorized plan and builds argv.

The bounded form (``context_tokens`` supplied) is the deterministic RC1 form:
it uses non-interactive I/O, a single turn and an explicit output-token limit.
The unbounded historical form remains available for compatibility, but it is
not the preferred path for reproducible measurement.

It never downloads models, installs llama.cpp, selects a model, measures
hardware or publishes evidence.
"""

from __future__ import annotations

import re
from typing import Any

from scripts.runtime_registry import RuntimeEntry
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec

DEFAULT_MAX_OUTPUT_TOKENS = 128
TOKENS_PER_SECOND_PATTERN = re.compile(
    r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE
)


class LlamaCppAdapter(RuntimeAdapter):
    """Canonical LEONES adapter for the local llama.cpp runtime."""

    runtime_id = "llama.cpp"
    adapter_id = "llama_cpp.v1.1"

    def prepare(
        self, plan: dict[str, Any], entry: RuntimeEntry
    ) -> RuntimeExecutionSpec:
        """Validate a plan and expose only the execution metadata we need."""
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
    """Build shell-free llama.cpp argv from explicit measurement parameters.

    ``context_tokens=None`` preserves the historical command shape. Supplying
    a context activates the bounded RC1 form so a benchmark cannot accidentally
    inherit llama.cpp's unlimited-generation default.
    """
    if max_output_tokens < 1:
        raise ValueError("max_output_tokens must be positive")

    command = [executable, "-m", model_path, "-p", prompt]

    if context_tokens is not None:
        if context_tokens < 1:
            raise ValueError("context_tokens must be positive")
        # These flags make subprocess behavior predictable: no interactive
        # prompt remains open, exactly one turn is executed, and generation is
        # bounded. The command is returned as argv, never assembled as a shell
        # string, so prompt/model paths cannot become shell syntax.
        command.extend(
            [
                "--simple-io",
                "--single-turn",
                "-c",
                str(context_tokens),
                "-n",
                str(max_output_tokens),
            ]
        )

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
    """Build llama.cpp argv only from an explicitly authorized plan."""
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not authorized")

    runtime_value = plan.get("runtime")
    runtime_id = (
        runtime_value.get("name")
        if isinstance(runtime_value, dict)
        else runtime_value
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
    """Return the single runtime pattern used to extract observed tok/s."""
    return TOKENS_PER_SECOND_PATTERN.pattern
