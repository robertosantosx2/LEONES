#!/usr/bin/env python3
"""Adapter for llama.cpp behind the LEONES runtime selection gate."""
from __future__ import annotations

import re
from typing import Any

TOKENS_PER_SECOND_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE)


def build_command(executable: str, model_path: str, prompt: str, *, context_tokens: int | None = None) -> list[str]:
    """Build a shell-free llama.cpp command."""
    command = [executable, "-m", model_path, "-p", prompt]
    if context_tokens is not None:
        if context_tokens < 1:
            raise ValueError("context_tokens must be positive")
        command.extend(["-c", str(context_tokens)])
    return command


def build_command_from_plan(plan: dict[str, Any], model_path: str, prompt: str, *, executable: str = "llama-cli", context_tokens: int | None = None) -> list[str]:
    """Build llama.cpp command only from a runtime-gate execution plan.

    Quantization is a property of the selected model artifact (normally the
    GGUF file), so the adapter deliberately does not invent a llama.cpp flag
    from its label. The plan must have been authorized by runtime_gate.py.
    """
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not authorized")
    if plan.get("runtime") != "llama.cpp":
        raise ValueError(f"unsupported runtime for llama.cpp adapter: {plan.get('runtime')!r}")
    if not plan.get("quantization"):
        raise ValueError("runtime plan has no quantization")
    return build_command(executable, model_path, prompt, context_tokens=context_tokens)


def tokens_per_second_pattern() -> str:
    return TOKENS_PER_SECOND_PATTERN.pattern
