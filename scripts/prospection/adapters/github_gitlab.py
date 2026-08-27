#!/usr/bin/env python3
"""Normalize GitHub/GitLab API search results into Atlas discoveries.

The caller supplies already-fetched API records. Keeping HTTP outside this
module makes rate limits, authentication and source-specific policies explicit.
"""

from __future__ import annotations
from typing import Any, Dict, Iterable


def normalize(
    record: Dict[str, Any], source_id: str, kind: str = "software"
) -> Dict[str, Any]:
    return {
        "type": kind,
        "name": record.get("name") or record.get("path") or record.get("full_name", ""),
        "organization": record.get("organization")
        or record.get("owner", {}).get("login", ""),
        "url": record.get("html_url") or record.get("web_url") or record.get("url", ""),
        "source": source_id,
        "license": (record.get("license") or {}).get("spdx_id", "")
        if isinstance(record.get("license"), dict)
        else record.get("license", ""),
        "description": record.get("description", ""),
        "default_branch": record.get("default_branch", ""),
        "evidence_url": record.get("html_url")
        or record.get("web_url")
        or record.get("url", ""),
        "observed_at": record.get("observed_at", ""),
        "evidence": {
            "source_id": source_id,
            "url": record.get("html_url")
            or record.get("web_url")
            or record.get("url", ""),
        },
    }


def emit(
    records: Iterable[Dict[str, Any]], source_id: str, kind: str = "software"
) -> Iterable[Dict[str, Any]]:
    for record in records:
        item = normalize(record, source_id, kind)
        if item["name"] and item["url"]:
            yield item
