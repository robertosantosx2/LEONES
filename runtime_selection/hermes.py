"""Hermes-backed model selection for RC3.

Hermes is used as the decision agent; LEONES remains the authority that
constrains the choice to the supplied candidate set and records provenance.
No runtime is started and no model is downloaded by this module.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from typing import Any

SCHEMA_VERSION = "hermes-model-selection.v1"


def hermes_available() -> bool:
    return shutil.which("hermes") is not None


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Hermes did not return a JSON object")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("Hermes selection response is not an object")
    return value


def select_model(
    candidates: list[dict[str, Any]],
    *,
    task: str = "general",
    hermes_command: str = "hermes",
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Ask Hermes to choose exactly one model from the supplied candidates.

    The candidate set is authoritative: Hermes may rank/explain candidates but
    cannot introduce a model that LEONES did not supply.
    """
    if not candidates:
        raise ValueError("Hermes selection requires at least one candidate")
    if shutil.which(hermes_command) is None:
        raise RuntimeError("Hermes is not installed; run scripts/install_hermes.sh")

    allowed = [c.get("model_id") for c in candidates]
    prompt = {
        "instruction": "Select exactly one candidate model for LEONES.",
        "task": task,
        "rules": [
            "Choose only a model_id present in candidates.",
            "Do not invent models, quantizations, hardware facts, or benchmark results.",
            "Return JSON only with selected_model_id, rationale, and confidence.",
        ],
        "candidates": candidates,
    }
    proc = subprocess.run(
        [hermes_command, "-z", json.dumps(prompt, ensure_ascii=False)],
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Hermes selection failed with exit code {proc.returncode}")

    response = _extract_json(proc.stdout)
    selected = response.get("selected_model_id")
    if selected not in allowed:
        raise ValueError(f"Hermes selected a model outside the candidate set: {selected!r}")

    return {
        "schema_version": SCHEMA_VERSION,
        "selector": "hermes",
        "selector_command": hermes_command,
        "task": task,
        "selected_model_id": selected,
        "rationale": str(response.get("rationale") or ""),
        "confidence": response.get("confidence"),
        "candidate_count": len(candidates),
        "execution_authorized": False,
        "measurement_authorized": False,
        "measured": False,
    }
