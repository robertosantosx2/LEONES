#!/usr/bin/env python3
"""Feed measured runtime evidence back into Atlas without changing provenance."""
from __future__ import annotations

from typing import Any

try:
    from scripts.enrich_measured_performance import enrich_measured_performance
    from scripts.validate_evidence import validate_evidence
except ModuleNotFoundError:  # ejecución directa
    from enrich_measured_performance import enrich_measured_performance
    from validate_evidence import validate_evidence


def integrate_measurements(rows: list[dict[str, Any]], measurements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add the latest compatible measured result to each Atlas row.

    Estimated/reported rows remain untouched. A measurement must retain its
    execution identity, timestamp and explicit real measurement kind when it
    enters Atlas; no value is promoted merely because it was copied into the
    catalog.
    """
    valid = []
    for measurement in measurements:
        if measurement.get("measurement_type") != "measured":
            continue
        evidence = {
            "evidence_type": measurement.get("evidence_type", "measured"),
            "execution_id": measurement.get("execution_id"),
            "measured_at": measurement.get("measured_at"),
            "measurement_kind": measurement.get("measurement_kind"),
        }
        validate_evidence(evidence)
        valid.append(measurement)

    result: list[dict[str, Any]] = []
    for row in rows:
        matches = [
            m for m in valid
            if (not row.get("model_id") or m.get("model_id") == row.get("model_id"))
            and m.get("hardware") == row.get("hardware")
            and m.get("runtime") == row.get("runtime")
        ]
        output = dict(row)
        if matches:
            measured = enrich_measured_performance(matches[-1])
            output["measured_tokens_per_second"] = measured["tokens_per_second"]
            output["measured_performance_class"] = measured["performance_class"]
            output["measurement_type"] = "measured"
            output["evidence_type"] = "measured"
            output["measurement_kind"] = "real"
            output["execution_id"] = measured["execution_id"]
            output["measured_at"] = measured["measured_at"]
        result.append(output)

    return result
