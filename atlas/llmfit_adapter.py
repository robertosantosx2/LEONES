"""Adapter from LLMFit-style estimates to the LEONES recommendation contract.

This module deliberately treats LLMFit output as *estimated* evidence. It never
promotes an estimate to a LEONES measurement or an external benchmark claim.
"""
from __future__ import annotations

from typing import Any


def llmfit_candidate_to_atlas(candidate: dict[str, Any], *, source_url: str = "https://www.llmfit.org/") -> dict[str, Any]:
    """Normalize one LLMFit candidate into an Atlas recommendation record."""
    model_id = candidate.get("id") or candidate.get("model_id")
    if not model_id:
        raise ValueError("LLMFit candidate requires id/model_id")

    parameters = candidate.get("parameters_b")
    quantization = candidate.get("quantization")
    memory = candidate.get("memory_gb")
    runtime = candidate.get("runtime") or candidate.get("backend")
    fits = candidate.get("fits_memory")
    if fits is True:
        cabe_status = "estimated"
    elif fits is False:
        cabe_status = "estimated"
    else:
        cabe_status = "unknown"

    recommendation = {
        "jgb": candidate.get("jgb"),
        "jgb_status": "verified" if candidate.get("jgb") is not None else "unknown",
        "cabe": fits if isinstance(fits, bool) else None,
        "cabe_status": cabe_status,
        "rula": None,
        "rula_status": "unknown",
        "fit_score": candidate.get("fit_score"),
        "performance_score": None,
        "economic_score": None,
        "uncertainty": candidate.get("uncertainty", 1.0),
        "ranking_basis": ["cabe", "evidence", "uncertainty"],
        "last_verified_at": None,
    }
    model_system = {
        "parameters_total_b": parameters,
        "parameters_active_b": candidate.get("active_parameters_b"),
        "quantization": quantization,
        "weight_memory_gb": candidate.get("weight_memory_gb", memory),
        "kv_cache_gb": candidate.get("kv_memory_gb"),
        "runtime_overhead_gb": candidate.get("runtime_overhead_gb"),
        "memory_margin_gb": candidate.get("memory_margin_gb"),
        "runtime": runtime,
        "runtime_version": candidate.get("runtime_version"),
        "backend": candidate.get("backend"),
        "context_length": candidate.get("context_length"),
    }
    return {
        "id": str(model_id),
        "kind": "model",
        "name": candidate.get("name") or str(model_id),
        "family": candidate.get("family"),
        "organization": candidate.get("organization"),
        "version": candidate.get("version"),
        "recommendation": recommendation,
        "model_system": model_system,
        "external_evidence": [{
            "source_type": "other",
            "url": source_url,
            "retrieved_at": candidate.get("retrieved_at"),
            "claim": "LLMFit estimate used for candidate fitting/ordering; not a LEONES measurement.",
            "source_record_id": candidate.get("source_record_id"),
        }],
        "evidence": {
            "state": "reported",
            "sources": [source_url],
            "retrieved_at": candidate.get("retrieved_at"),
            "evidence_type": "external",
        },
        "quality_flags": [{
            "flag_type": "unverified",
            "severity": "medium",
            "field_name": "recommendation.cabe",
            "message": "CABE/RULA values derived from LLMFit are estimates until verified by LEONES.",
            "detected_at": candidate.get("retrieved_at") or "unknown",
            "resolved_at": None,
        }],
        "lifecycle": "active",
    }


def to_runtime_selection(record: dict[str, Any], *, trusted_runtime_command: list[str] | None = None) -> dict[str, Any]:
    """Produce a runtime-selection.v1 candidate without fabricating authorization."""
    rec = record.get("recommendation", {})
    system = record.get("model_system", {})
    runtime = system.get("runtime")
    command = trusted_runtime_command if trusted_runtime_command else None
    return {
        "schema": "runtime-selection.v1",
        "execution_authorized": bool(command and rec.get("rula") is True),
        "model": {"id": record["id"], "revision": record.get("version")},
        "runtime": {"name": runtime, "command": command},
        "hardware": {"memory_margin_gb": system.get("memory_margin_gb")},
        "inference": {"context_length": system.get("context_length")},
        "selection": {
            "source": "llmfit",
            "evidence_level": "Estimated",
            "cabe_status": rec.get("cabe_status"),
            "rula_status": rec.get("rula_status"),
        },
    }
