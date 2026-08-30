#!/usr/bin/env python3
"""Trusted V1.1 adapter for llama.cpp."""

from __future__ import annotations
import os
import re
from typing import Any
from scripts.runtimes.base import RuntimeAdapter, RuntimeExecutionSpec
from scripts.runtime_registry import RuntimeEntry

TOKENS_PER_SECOND_PATTERN = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*tok/s", re.IGNORECASE)


class LlamaCppAdapter(RuntimeAdapter):
    runtime_id = "llama.cpp"
    adapter_id = "llama_cpp.v1.1"

    def validate(self, plan: dict[str, Any], entry: RuntimeEntry) -> None:
        """Validate the physical llama.cpp contract before authorization.

        A trusted executable alone is not enough to authorize physical
        execution: llama.cpp also needs an explicit GGUF model artifact with
        provenance. This prevents a seemingly valid selection from becoming
        an executable plan with an unresolved model reference.
        """
        super().validate(plan, entry)
        model_format = str(plan.get("model_format") or "").upper()
        if model_format != "GGUF":
            raise ValueError("llama.cpp physical plan requires model_format=GGUF")
        artifact = plan.get("model_artifact")
        if not isinstance(artifact, dict):
            raise ValueError("llama.cpp physical plan requires model_artifact")
        model_path = artifact.get("path")
        model_sha256 = artifact.get("sha256")
        if not isinstance(model_path, str) or not model_path:
            raise ValueError("model_artifact.path is required")
        if not isinstance(model_sha256, str) or not model_sha256:
            raise ValueError("model_artifact.sha256 is required")

    def prepare(
        self, plan: dict[str, Any], entry: RuntimeEntry
    ) -> RuntimeExecutionSpec:
        self.validate(plan, entry)
        trusted_entrypoint = plan.get("trusted_entrypoint") or list(entry.entrypoint["argv"])
        artifact = plan["model_artifact"]
        model_path = artifact["path"]
        if not trusted_entrypoint or not all(isinstance(x, str) for x in trusted_entrypoint):
            raise ValueError("trusted llama.cpp entrypoint is invalid")
        executable = trusted_entrypoint[0]
        if os.path.basename(executable) != "llama-cli" or len(trusted_entrypoint) != 1:
            raise ValueError("llama.cpp physical plan requires trusted llama-cli executable")
        context_tokens = (plan.get("workload") or {}).get("context_tokens")
        command = build_command_prefix(
            executable,
            model_path,
            context_tokens=context_tokens,
        )
        metadata: dict[str, Any] = {
            "metrics": entry.metrics,
            "format": "GGUF",
            "execution_command": command,
            "model_artifact": dict(artifact),
        }
        return RuntimeExecutionSpec(
            self.runtime_id,
            self.adapter_id,
            plan["model_id"],
            tuple(command),
            metadata,
        )


ADAPTER = LlamaCppAdapter()


def build_command_prefix(
    executable: str,
    model_path: str,
    *,
    context_tokens: int | None = None,
) -> list[str]:
    if not executable or os.path.basename(executable) != "llama-cli":
        raise ValueError("executable is not the trusted llama.cpp entrypoint")
    if not model_path:
        raise ValueError("model_path is required")
    command = [executable, "-m", model_path]
    if context_tokens is not None:
        if context_tokens < 1:
            raise ValueError("context_tokens must be positive")
        command.extend(["-c", str(context_tokens)])
    command.append("-p")
    return command


def build_command(
    executable: str, model_path: str, prompt: str, *, context_tokens: int | None = None
) -> list[str]:
    command = build_command_prefix(executable, model_path, context_tokens=context_tokens)
    command.append(prompt)
    return command


def build_command_from_plan(
    plan: dict[str, Any],
    model_path: str,
    prompt: str,
    *,
    executable: str = "llama-cli",
    context_tokens: int | None = None,
) -> list[str]:
    if plan.get("execution_authorized") is not True:
        raise ValueError("runtime plan is not authorized")
    runtime_value = plan.get("runtime")
    runtime_id = (
        runtime_value.get("name") if isinstance(runtime_value, dict) else runtime_value
    )
    if runtime_id != "llama.cpp":
        raise ValueError("unsupported runtime for llama.cpp adapter")
    if os.path.basename(executable) != "llama-cli":
        raise ValueError("executable is not the trusted llama.cpp registry entrypoint")
    if not plan.get("quantization"):
        raise ValueError("runtime plan has no quantization")
    return build_command(executable, model_path, prompt, context_tokens=context_tokens)


def tokens_per_second_pattern() -> str:
    return TOKENS_PER_SECOND_PATTERN.pattern
