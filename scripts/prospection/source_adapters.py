#!/usr/bin/env python3
"""Auditable source registry for the LEONES daily prospection layer.

Adapters emit discoveries; they never publish directly to Atlas. Each source
has an explicit URL, category and trust label so provenance survives ingestion.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable


@dataclass(frozen=True)
class Source:
    id: str
    kind: str
    description: str
    url: str
    trust: str = "external"


SOURCES = (
    Source(
        "huggingface-models",
        "models",
        "Hugging Face model discovery",
        "https://huggingface.co/models",
    ),
    Source(
        "github", "software", "GitHub repositories and releases", "https://github.com/"
    ),
    Source(
        "huggingface-spaces",
        "agents",
        "Hugging Face Spaces discovery",
        "https://huggingface.co/spaces",
    ),
    Source(
        "huggingface-papers",
        "research",
        "Research and paper discovery",
        "https://huggingface.co/papers",
    ),
)


def validate_discovery(record: Dict[str, Any]) -> bool:
    return bool(
        record.get("name")
        and (record.get("url") or record.get("source"))
        and record.get("type")
    )


def emit(records: Iterable[Dict[str, Any]]) -> Iterable[Dict[str, Any]]:
    for record in records:
        if validate_discovery(record):
            yield record
