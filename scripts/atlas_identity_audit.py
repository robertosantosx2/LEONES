#!/usr/bin/env python3
"""Audit canonical identity in the Atlas prospection feed.

This script answers one simple question:

    "When two rows talk about a model, do they appear to describe the same
     underlying identity, or do we need a human to review them?"

It is intentionally an *auditor*, not a merger.  A duplicate-looking pair is
reported for review; records are never deleted or silently combined.

The intended reader is a human with basic programming knowledge.  The main
steps are therefore kept explicit:

1. read the operational CSV feed;
2. calculate a stable identity key for every row;
3. group rows by that key;
4. classify each group;
5. write a CSV that a human can inspect.
"""

from __future__ import annotations

import collections
import csv
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
OUT = ROOT / "data/prospection/atlas_identity_audit.csv"


def norm(value: object) -> str:
    """Make a value comparable without changing the original stored value.

    We lowercase and replace punctuation with spaces only for the *comparison
    key*.  The original spelling remains in the audit output so a human can
    inspect it.
    """
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def repo_key(row: dict[str, str]) -> str:
    """Extract a comparable repository identity from a forge URL.

    GitHub and Hugging Face URLs normally contain ``owner/repository`` in their
    path.  If the URL is not one of those known forges, we deliberately return
    an empty key instead of guessing.
    """
    url = (row.get("repository_url") or row.get("source_url") or "").strip().rstrip("/")
    match = re.search(r"(?:github\.com|huggingface\.co)/([^/]+/[^/?#]+)", url, re.I)
    return norm(match.group(1)) if match else ""


def identity(row: dict[str, str]) -> str:
    """Choose the canonical comparison key using the project precedence rule.

    Strongest evidence comes first:

    1. explicit model_id;
    2. canonical repository path;
    3. organization + model name.

    Name matching is deliberately a fallback.  The function never says that
    two records are definitely the same model; it only creates a key for the
    audit grouping step.
    """
    model_id = norm(row.get("model_id"))
    repository = repo_key(row)
    organization = norm(row.get("organization"))
    model_name = norm(row.get("model_name"))
    return model_id or repository or (organization + " " + model_name).strip()


def classify(items: list[tuple[int, dict[str, str]]]) -> tuple[str, str]:
    """Classify a group of rows and assign a review risk.

    Multiple rows are not automatically errors.  They may be legitimate
    configurations of one model, such as different quantizations or hardware.
    Such groups are therefore kept separate and marked for review.
    """
    if len(items) == 1:
        return "unique", "low"

    variants = {norm(row.get("quantization")) for _, row in items}
    hardware = {norm(row.get("hardware_id")) for _, row in items}
    names = {norm(row.get("model_name")) for _, row in items}

    if len(variants) > 1 or len(hardware) > 1:
        return "same-model-multiple-artifacts-or-configs", "review"
    if len(names) > 1:
        return "possible-collision", "high"
    return "duplicate-candidate", "high"


def main() -> None:
    """Run the complete audit and write the human-readable CSV report."""
    if not FEED.exists():
        raise SystemExit(f"Missing Atlas feed: {FEED}")

    # DictReader turns each CSV row into a dictionary whose keys are the
    # column names.  Keeping the rows in memory is appropriate for the current
    # feed size and makes the grouping logic easy to understand.
    with FEED.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    # ``defaultdict(list)`` creates one bucket per identity key.  We keep the
    # original row number because the report must let a human find the source
    # row again in the feed.
    groups: dict[str, list[tuple[int, dict[str, str]]]] = collections.defaultdict(list)
    for row_number, row in enumerate(rows, start=1):
        key = identity(row)
        if key:
            groups[key].append((row_number, row))

    output_rows: list[dict[str, str]] = []

    # Every group gets one classification.  That classification is copied to
    # every row in the group so filtering the resulting CSV is straightforward.
    for key, items in groups.items():
        status, risk = classify(items)
        for row_number, row in items:
            output_rows.append(
                {
                    "identity_key": key,
                    "row_number": str(row_number),
                    "model_id": row.get("model_id", ""),
                    "model_name": row.get("model_name", ""),
                    "organization": row.get("organization", ""),
                    "repository_url": row.get("repository_url", ""),
                    "quantization": row.get("quantization", ""),
                    "hardware_id": row.get("hardware_id", ""),
                    "status": status,
                    "risk": risk,
                    "action": "retain" if risk == "low" else "review-before-merge",
                }
            )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "identity_key",
        "row_number",
        "model_id",
        "model_name",
        "organization",
        "repository_url",
        "quantization",
        "hardware_id",
        "status",
        "risk",
        "action",
    ]
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output_rows)

    status_counts = collections.Counter(row["status"] for row in output_rows)
    duplicate_groups = sum(1 for items in groups.values() if len(items) > 1)
    print(
        f"Identity audit: rows={len(rows)} keys={len(groups)} "
        f"unique={status_counts['unique']} duplicate_groups={duplicate_groups} "
        f"output={OUT}"
    )


if __name__ == "__main__":
    main()
