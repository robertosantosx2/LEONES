#!/usr/bin/env python3
"""Enforce the LEONES evidence ladder: estimated -> reported -> measured -> verified.

The four labels describe provenance, not quality or model performance. In
particular, a reported number cannot become measured merely by renaming it.
Measured evidence needs a concrete execution id, timestamp and explicit
real-world measurement kind; synthetic runs can never be promoted to measured
or verified performance evidence.
"""

from __future__ import annotations

from typing import Any

EVIDENCE_TYPES = ("estimated", "reported", "measured", "verified")
REAL_MEASUREMENT_KIND = "real"
SYNTHETIC_MARKERS = {
    "synthetic",
    "simulated",
    "simulation",
    "fixture",
    "fake",
    "controlled",
}


def _is_synthetic(evidence: dict[str, Any]) -> bool:
    """Return True when any explicit run/measurement provenance says synthetic."""
    for field in (
        "measurement_kind",
        "measurement_type",
        "run_type",
        "execution_kind",
        "provenance",
    ):
        value = evidence.get(field)
        if isinstance(value, str) and value.strip().lower() in SYNTHETIC_MARKERS:
            return True
    return False


def validate_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Validate provenance metadata without promoting its evidence level."""
    if evidence.get("evidence_type") not in EVIDENCE_TYPES:
        raise ValueError(
            "evidence_type must be estimated, reported, measured or verified"
        )

    evidence_type = evidence["evidence_type"]
    if evidence_type in {"measured", "verified"}:
        if _is_synthetic(evidence):
            raise ValueError("synthetic evidence cannot be measured or verified")
        if not evidence.get("execution_id"):
            raise ValueError("measured/verified evidence requires execution_id")
        if not evidence.get("measured_at"):
            raise ValueError("measured/verified evidence requires measured_at")
        if evidence.get("measurement_kind") != REAL_MEASUREMENT_KIND:
            raise ValueError(
                "measured/verified evidence requires measurement_kind=real"
            )

    if evidence_type == "verified":
        for field in ("verified_at", "verifier", "verification_method"):
            if not evidence.get(field):
                raise ValueError(f"verified evidence requires {field}")

    return dict(evidence)


def promote_to_verified(
    evidence: dict[str, Any], *, verifier: str, method: str, verified_at: str
) -> dict[str, Any]:
    """Promote measured evidence only after explicit independent verification."""
    current = validate_evidence(evidence)
    if current["evidence_type"] != "measured":
        raise ValueError("only measured evidence can be promoted to verified")
    current.update(
        {
            "evidence_type": "verified",
            "verified_at": verified_at,
            "verifier": verifier,
            "verification_method": method,
        }
    )
    return validate_evidence(current)
