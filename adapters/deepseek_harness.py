"""Normalization boundary for DeepSeek Harness observations."""


def normalize_result(data: dict) -> dict:
    return {
        "source": "deepseek-harness",
        "task": data.get("task"),
        "status": data.get("status"),
        "tools": data.get("tools", []),
        "trajectory": data.get("trajectory"),
        "outcome": data.get("outcome"),
        "duration_seconds": data.get("duration_seconds"),
        "cost": data.get("cost"),
        "safety_events": data.get("safety_events", []),
        "artifacts": data.get("artifacts", []),
        "error": data.get("error"),
    }
