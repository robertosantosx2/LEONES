"""Compute comparable estimator errors against an existing LEONES measurement."""

from __future__ import annotations


def error_metrics(prediction: float | None, measured: float | None) -> dict[str, float | None]:
    if prediction is None or measured is None or measured <= 0:
        return {"abs": None, "pct": None, "bias": None, "factor": None}
    delta = prediction - measured
    return {
        "abs": abs(delta),
        "pct": abs(delta) / measured * 100,
        "bias": delta,
        "factor": prediction / measured,
    }


def compare_estimators(*, llmfit: float | None, canirun: float | None, measured: float | None) -> dict:
    """Return analysis-only data; never promote estimates to measurements."""
    return {
        "llmfit": {"estimated_tps": llmfit, "error": error_metrics(llmfit, measured)},
        "canirun": {"estimated_tps": canirun, "error": error_metrics(canirun, measured)},
        "measured_tps": measured,
    }
