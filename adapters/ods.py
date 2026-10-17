"""Normalization boundary for ODS runtime observations."""


def normalize_result(data: dict) -> dict:
    return {
        "source": "ods",
        "backend": data.get("backend"),
        "backend_version": data.get("backend_version"),
        "model": data.get("model"),
        "model_revision": data.get("model_revision"),
        "quantization": data.get("quantization"),
        "tokens_per_second": data.get("tokens_per_second"),
        "total_time_seconds": data.get("total_time_seconds"),
        "error": data.get("error"),
    }
