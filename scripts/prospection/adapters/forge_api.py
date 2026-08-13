#!/usr/bin/env python3
"""Generic API adapter contract for Forgejo/Gitea/GitLab-like forges.

The adapter deliberately returns evidence-rich discovery records and does not
publish them. Concrete instances can configure endpoint/API details without
changing the Atlas contract.
"""
from __future__ import annotations
from typing import Any, Dict, Iterable


def discovery(*, source_id: str, name: str, url: str, kind: str, license: str | None = None, evidence_url: str | None = None, observed_at: str | None = None, **extra: Any) -> Dict[str, Any]:
    return {
        "type": kind,
        "name": name,
        "url": url,
        "source": source_id,
        "license": license or "",
        "evidence_url": evidence_url or url,
        "observed_at": observed_at or "",
        "evidence": {"source_id": source_id, "url": evidence_url or url},
        **extra,
    }


def emit(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for record in records:
        if record.get("name") and record.get("url") and record.get("source"):
            yield record
