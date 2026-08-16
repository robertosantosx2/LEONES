#!/usr/bin/env python3
"""Promote only sufficiently evidenced feed rows into the canonical Atlas.

This script is the safety boundary between the operational prospection feed and
``atlas/catalog.json``.  A feed row is *not* an Atlas record just because it
exists in the feed: it must have an explicit ``evidence_status=verified`` and a
usable identity/source.  Unknown values remain unknown; the script never turns
an empty field into zero and never invents benchmark, JGB, CABE or RULA values.

For a beginner, the flow is:

    atlas_feed.csv
          |
          | keep only verified rows
          v
    canonical identity + evidence
          |
          v
    atlas/catalog.json

The operation is deliberately additive. Existing canonical records are kept
unless a record with the same canonical id is regenerated from a newer verified
feed observation. No destructive deduplication is performed here.
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
CATALOG = ROOT / "atlas/catalog.json"
REPORT = ROOT / "data/prospection/atlas_promotion_report.json"


def text(value: object) -> str:
    """Return a trimmed string, treating missing values as empty."""
    return str(value or "").strip()


def number(value: object):
    """Convert a numeric CSV value without inventing a value when it is blank."""
    raw = text(value)
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def integer(value: object):
    """Convert a whole-number CSV value, otherwise keep it unknown."""
    raw = text(value)
    if not raw:
        return None
    try:
        return int(float(raw))
    except ValueError:
        return None


def canonical_id(row: dict[str, str]) -> str:
    """Choose a stable identity in the project's documented precedence order."""
    model_id = text(row.get("model_id"))
    if model_id:
        return model_id

    repository = text(row.get("repository_url")) or text(row.get("source_url"))
    if repository:
        parsed = urlparse(repository)
        path = parsed.path.strip("/")
        if path:
            return path.lower()

    organization = text(row.get("organization"))
    name = text(row.get("model_name"))
    return re.sub(r"[^a-z0-9._/-]+", "-", f"{organization}/{name}".lower()).strip("-")


def source_type(url: str) -> str:
    """Map a source URL to the Atlas evidence vocabulary."""
    host = urlparse(url).netloc.lower()
    if "huggingface.co" in host:
        return "hugging_face"
    if "chat.lmsys.org" in host or "lmarena.ai" in host:
        return "lm_arena"
    if "artificialanalysis.ai" in host:
        return "artificial_analysis"
    return "other"


def evidence_objects(row: dict[str, str]) -> list[dict]:
    """Build one evidence object per useful external URL, without guessing claims."""
    objects = []
    retrieved = text(row.get("technical_evidence_checked_at")) or None
    for field in ("technical_evidence_url", "source_url", "repository_url", "weights_url", "code_url"):
        url = text(row.get(field))
        if not url or any(item["url"] == url for item in objects):
            continue
        objects.append({
            "source_type": source_type(url),
            "url": url,
            "retrieved_at": retrieved,
            "claim": None,
            "source_record_id": text(row.get("source_id")) or None,
        })
    return objects


def build_record(row: dict[str, str]) -> dict:
    """Translate one verified operational row into the canonical Atlas shape."""
    rid = canonical_id(row)
    evidence_urls = evidence_objects(row)

    record = {
        "id": rid,
        "kind": "model",
        "name": text(row.get("model_name")) or rid,
        "family": None,
        "organization": text(row.get("organization")) or None,
        "version": None,
        "architecture": {},
        "artifacts": {},
        "execution": {},
        "model_system": {},
        "external_evidence": evidence_urls,
        "experiments": [],
        "evaluation": [],
        "quality_flags": [],
        "evidence": {
            "state": "verified",
            "sources": [item["url"] for item in evidence_urls],
            "retrieved_at": text(row.get("technical_evidence_checked_at")) or None,
            "evidence_type": "external",
        },
        "lifecycle": "active",
    }

    architecture = text(row.get("architecture"))
    if architecture:
        record["architecture"]["name"] = architecture

    for key in ("runtime", "runtime_version", "backend", "format", "quantization", "hardware_id", "workload"):
        value = text(row.get(key))
        if value:
            record["execution"][key] = value

    model_system = {
        "parameters_total_b": number(row.get("parameters_total_b")),
        "parameters_active_b": number(row.get("parameters_active_b")),
        "quantization": text(row.get("quantization")) or None,
        "weight_memory_gb": number(row.get("weight_memory_gb")),
        "runtime": text(row.get("runtime")) or None,
        "runtime_version": text(row.get("runtime_version")) or None,
        "backend": text(row.get("backend")) or None,
        "context_length": integer(row.get("context_tokens")),
    }
    # The schema permits nulls, so keeping these explicit makes the semantics
    # obvious while still avoiding fabricated values.
    record["model_system"] = model_system

    jgb = number(row.get("jgb_level"))
    if jgb is not None:
        record["recommendation"] = {
            "jgb": jgb,
            "jgb_status": "provisional",
            "cabe": None,
            "cabe_status": "unknown",
            "rula": None,
            "rula_status": "unknown",
            "fit_score": None,
            "performance_score": None,
            "economic_score": None,
            "uncertainty": None,
            "ranking_basis": ["jgb", "evidence"],
            "last_verified_at": text(row.get("technical_evidence_checked_at")) or None,
        }

    notes = text(row.get("notes"))
    if notes:
        record["artifacts"]["notes"] = notes

    return record


def main() -> int:
    """Run the promotion and write a machine-readable audit report."""
    if not FEED.exists():
        raise SystemExit(f"Missing feed: {FEED}")

    with FEED.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))

    catalog = {"atlas_version": "0.2", "generated_at": None, "records": [], "notes": []}
    if CATALOG.exists():
        catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    existing = {record.get("id"): record for record in catalog.get("records", []) if record.get("id")}
    verified = 0
    promoted = 0
    rejected = 0
    no_identity = 0

    for row in rows:
        if text(row.get("evidence_status")).lower() != "verified":
            rejected += 1
            continue
        verified += 1
        rid = canonical_id(row)
        if not rid:
            no_identity += 1
            continue
        existing[rid] = build_record(row)
        promoted += 1

    catalog["records"] = sorted(existing.values(), key=lambda item: item.get("id", ""))
    catalog["generated_at"] = datetime.now(timezone.utc).isoformat()
    catalog["notes"] = [
        "Only feed rows with evidence_status=verified are promoted by this process.",
        "Unknown values remain unknown; empty fields are never interpreted as zero.",
        "External evidence is not automatically a LEONES measurement.",
        "Identity collisions are reviewed separately and are never destructively merged here.",
    ]

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = {
        "generated_at": catalog["generated_at"],
        "feed_rows": len(rows),
        "verified_rows": verified,
        "promoted_rows": promoted,
        "rejected_not_verified": rejected,
        "rows_without_identity": no_identity,
        "canonical_records": len(catalog["records"]),
        "policy": "verified-only, non-destructive, no invented values",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
