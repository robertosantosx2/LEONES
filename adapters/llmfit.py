"""Boundary for the optional llmfit preselector."""


def normalize_estimate(data: dict) -> dict:
    """Keep llmfit estimates explicitly separate from LEONES measurements."""
    return {
        "llmfit_quality_estimate": data.get("quality"),
        "llmfit_speed_estimate": data.get("speed"),
        "llmfit_fit": data.get("fit"),
        "llmfit_context_fit": data.get("context_fit"),
        "llmfit_quantization": data.get("quantization"),
        "llmfit_run_mode": data.get("run_mode"),
        "llmfit_memory_estimate": data.get("memory"),
        "llmfit_runtime": data.get("runtime"),
        "llmfit_source_version": data.get("source_version"),
    }
