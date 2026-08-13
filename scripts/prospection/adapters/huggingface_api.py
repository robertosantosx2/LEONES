#!/usr/bin/env python3
"""Evidence-preserving Hugging Face discovery adapter contract."""
from __future__ import annotations
from typing import Any, Dict, Iterable


def discovery(*, source_id: str, name: str, url: str, kind: str = "model", license: str | None = None, observed_at: str | None = None, **extra: Any) -> Dict[str, Any]:
    return {
        "type": kind,
        "name": name,
        "url": url,
        "source": source_id,
        "license": license or "",
        "evidence_url": url,
        "observed_at": observed_at or "",
        "evidence": {"source_id": source_id, "url": url},
        **extra,
    }


def emit(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for record in records:
        if record.get("name") and record.get("url"):
            yield record
