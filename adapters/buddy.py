"""Normalization boundary for Buddy harness observations."""


def normalize_result(data: dict) -> dict:
    return {
        "source": "buddy",
        "task": data.get("task"),
        "status": data.get("status"),
        "steps": data.get("steps"),
        "trajectory": data.get("trajectory"),
        "outcome": data.get("outcome"),
        "artifacts": data.get("artifacts", []),
        "duration_seconds": data.get("duration_seconds"),
        "error": data.get("error"),
    }
