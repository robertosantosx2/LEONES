"""RC3 model-artifact resolution boundary.

External model evidence may identify a model and quantization class without
identifying a concrete local artifact. This module makes that distinction
explicit and prevents unresolved artifacts from being treated as executable.
"""
from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "model-artifact.v1"


def resolve_artifact(
    candidate: dict[str, Any],
    *,
    source_repo: str | None = None,
    artifact_format: str | None = None,
    artifact_filename: str | None = None,
    revision: str | None = None,
    sha256: str | None = None,
) -> dict[str, Any]:
    """Create an auditable artifact record without downloading anything.

    A repository-level resolution is deliberately not considered executable.
    A concrete filename, revision and SHA-256 are required before preparation
    or execution can be authorized by a later layer.
    """
    model_id = candidate.get("model_id")
    if not model_id:
        raise ValueError("candidate model_id is required")

    quantization_bits = candidate.get("quantization_bits")
    if quantization_bits is None:
        raise ValueError("candidate quantization_bits is required")

    status = "resolved" if artifact_filename and revision and sha256 else "source_resolved"
    executable = bool(status == "resolved")

    return {
        "schema_version": SCHEMA_VERSION,
        "model_id": model_id,
        "model_name": candidate.get("name", model_id),
        "parameters_b": candidate.get("parameters_b"),
        "quantization_bits": quantization_bits,
        "artifact": {
            "status": status,
            "source_repo": source_repo,
            "format": artifact_format,
            "filename": artifact_filename,
            "revision": revision,
            "sha256": sha256,
        },
        "executable": executable,
        "download_performed": False,
        "measurement_authorized": False,
        "resolution_required_before_execution": not executable,
    }


def validate_artifact(record: dict[str, Any]) -> None:
    """Enforce the boundary between source resolution and a concrete artifact."""
    if record.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported model-artifact schema")
    artifact = record.get("artifact") or {}
    if not record.get("model_id"):
        raise ValueError("model_id is required")
    if artifact.get("status") not in {"source_resolved", "resolved"}:
        raise ValueError("invalid artifact resolution status")
    if record.get("download_performed") is not False:
        raise ValueError("artifact resolver must not download artifacts")
    if record.get("measurement_authorized") is not False:
        raise ValueError("artifact resolution cannot authorize measurement")

    concrete = all(artifact.get(k) for k in ("filename", "revision", "sha256"))
    if artifact.get("status") == "resolved" and not concrete:
        raise ValueError("resolved artifact requires filename, revision and sha256")
    if record.get("executable") and not concrete:
        raise ValueError("unresolved artifact cannot be executable")
