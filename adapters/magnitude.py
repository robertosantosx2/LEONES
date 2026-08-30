"""Normalization boundary for Magnitude observations."""


def normalize_profile(data: dict) -> dict:
    return {
        "source": "magnitude",
        "hardware_profile": data.get("hardware_profile"),
        "model": data.get("model"),
        "runtime": data.get("runtime"),
        "estimated_tokens_per_second": data.get("tokens_per_second"),
        "source_version": data.get("source_version"),
    }
