#!/usr/bin/env python3
"""Preflight checks for the canonical local A01 runtime."""
from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimePreflight:
    runtime: str
    available: bool
    model_id: str
    model_available: bool
    reason: str | None = None
    installed_models: tuple[str, ...] = ()


def _ollama_models() -> tuple[str, ...]:
    """Return exact Ollama model names currently installed on the host."""
    if shutil.which("ollama") is None:
        return ()
    try:
        completed = subprocess.run(
            ["ollama", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return ()
    if completed.returncode != 0:
        return ()
    models: list[str] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line or line.upper().startswith("NAME"):
            continue
        name = line.split()[0]
        if name:
            models.append(name)
    return tuple(models)


def check_ollama_model(model_id: str) -> RuntimePreflight:
    """Check Ollama and require an exact installed model name.

    A Hugging Face/GGUF identifier is never treated as an Ollama model name
    unless Ollama explicitly reports that exact name as installed.
    """
    model_id = str(model_id or "").strip()
    if shutil.which("ollama") is None:
        return RuntimePreflight(
            runtime="ollama",
            available=False,
            model_id=model_id,
            model_available=False,
            reason="ollama_not_in_path",
        )
    models = _ollama_models()
    if model_id not in models:
        return RuntimePreflight(
            runtime="ollama",
            available=True,
            model_id=model_id,
            model_available=False,
            reason="model_not_installed_in_ollama",
            installed_models=models,
        )
    return RuntimePreflight(
        runtime="ollama",
        available=True,
        model_id=model_id,
        model_available=True,
        installed_models=models,
    )
