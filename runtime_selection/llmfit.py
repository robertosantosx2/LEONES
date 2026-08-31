"""LLMFit integration boundary for RC2 hardware intelligence.

This module deliberately does not implement model-fit heuristics. It consumes
LLMFit's machine-readable output and normalises the result for LEONES.

No installation, download, benchmark, or network operation is performed here.
The caller decides whether and when to invoke the external ``llmfit`` command.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import subprocess
from typing import Any, Mapping, Sequence


class LLMFitError(RuntimeError):
    """Raised when LLMFit is unavailable or returns invalid output."""


@dataclass(frozen=True)
class LLMFitResult:
    """Normalised, provenance-preserving LLMFit result."""

    command: tuple[str, ...]
    version: str | None
    system: Mapping[str, Any]
    models: Sequence[Mapping[str, Any]]
    raw: Mapping[str, Any]


def executable() -> str | None:
    """Return the resolved LLMFit executable without executing it."""

    return shutil.which("llmfit")


def build_recommend_command(
    *,
    limit: int = 5,
    use_case: str | None = None,
    max_context: int | None = None,
) -> list[str]:
    """Build a read-only JSON recommendation command."""

    if limit < 1:
        raise ValueError("limit must be >= 1")

    command = ["llmfit", "recommend", "--json", "--limit", str(limit)]
    if use_case:
        command.extend(["--use-case", use_case])
    if max_context is not None:
        if max_context < 1:
            raise ValueError("max_context must be >= 1")
        command.extend(["--max-context", str(max_context)])
    return command


def run_recommend(
    *,
    limit: int = 5,
    use_case: str | None = None,
    max_context: int | None = None,
    timeout_seconds: int = 30,
) -> LLMFitResult:
    """Run LLMFit recommendations and preserve its raw provenance."""

    command = build_recommend_command(
        limit=limit, use_case=use_case, max_context=max_context
    )
    if executable() is None:
        raise LLMFitError("llmfit executable not found")

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise LLMFitError(f"LLMFit execution failed: {exc}") from exc

    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise LLMFitError(f"LLMFit exited with {completed.returncode}: {detail}")

    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise LLMFitError("LLMFit did not return valid JSON") from exc

    if not isinstance(raw, dict):
        raise LLMFitError("LLMFit JSON root must be an object")

    models = raw.get("models", [])
    if not isinstance(models, list):
        raise LLMFitError("LLMFit JSON field 'models' must be a list")

    system = raw.get("system", {})
    if not isinstance(system, dict):
        system = {}

    version = raw.get("version")
    return LLMFitResult(
        command=tuple(command),
        version=version if isinstance(version, str) else None,
        system=system,
        models=tuple(m for m in models if isinstance(m, dict)),
        raw=raw,
    )


def normalise_hardware(result: LLMFitResult) -> dict[str, Any]:
    """Map LLMFit system data without inventing missing values."""

    source = result.system
    keys = ("os", "architecture", "cpu", "ram_gb", "gpu", "vram_gb", "backend")
    return {
        "source": "llmfit",
        "source_version": result.version,
        **{key: source.get(key) for key in keys},
        "raw": dict(source),
    }


def normalise_candidates(result: LLMFitResult) -> list[dict[str, Any]]:
    """Expose candidates while retaining LLMFit's estimates as estimates."""

    candidates: list[dict[str, Any]] = []
    for rank, model in enumerate(result.models, start=1):
        candidates.append(
            {
                "rank": rank,
                "source": "llmfit",
                "model": model.get("name") or model.get("id"),
                "fit": model.get("fit"),
                "estimated_tps": model.get("estimated_tps")
                or model.get("tps"),
                "quantization": model.get("quantization")
                or model.get("quant"),
                "raw": dict(model),
            }
        )
    return candidates
