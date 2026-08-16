#!/usr/bin/env python3
"""Create deterministic quality flags for the Atlas discovery feed.

A quality flag is a warning for a human or a later automated step.  It is not
an assertion that the data is false, and this script never changes the source
feed or upgrades an evidence state.

For a beginner, the workflow is:

    feed CSV
       ↓
    inspect required fields
       ↓
    inspect evidence state
       ↓
    look for simple identity collisions
       ↓
    write a list of flags

Missing information stays missing.  In particular, an empty value is never
converted to zero.
"""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data/prospection/atlas_feed.csv"
OUT = ROOT / "data/prospection/atlas_quality_flags.csv"

FIELDS = [
    "entity_type",
    "entity_id",
    "flag_type",
    "severity",
    "field_name",
    "message",
    "detected_at",
    "resolved_at",
    "resolution",
]

# These are the minimum fields that a discovery row needs before it can be
# considered a useful candidate.  This is deliberately a small list: a newly
# discovered project may legitimately lack benchmark or hardware information.
REQUIRED = ["model_id", "model_name", "source_url"]


def add_flag(
    flags: list[dict[str, str]],
    *,
    entity_id: str,
    flag_type: str,
    severity: str,
    field_name: str,
    message: str,
    detected_at: str,
) -> None:
    """Append one structured warning to the report.

    Keeping this operation in one function makes the output contract obvious
    and prevents different checks from accidentally producing different CSV
    shapes.
    """
    flags.append(
        {
            "entity_type": "model",
            "entity_id": entity_id,
            "flag_type": flag_type,
            "severity": severity,
            "field_name": field_name,
            "message": message,
            "detected_at": detected_at,
            "resolved_at": "",
            "resolution": "",
        }
    )


def main() -> None:
    """Read the feed, create flags, and write the deterministic report."""
    flags: list[dict[str, str]] = []
    now = datetime.now(timezone.utc).isoformat()

    # A missing feed is an infrastructure problem, not a data-quality problem.
    # We still create an empty report so downstream tooling has a predictable
    # file to consume.
    if not IN.exists():
        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8", newline="") as handle:
            csv.DictWriter(handle, fieldnames=FIELDS).writeheader()
        return

    with IN.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    # ``seen`` groups rows by the human-visible organization/model name.  This
    # is intentionally weaker than the canonical identity audit.  Its purpose
    # is to catch suspicious cases early, not to decide that two records are
    # definitely duplicates.
    seen: dict[tuple[str, str], list[str]] = {}

    for row in rows:
        entity_id = row.get("model_id", "") or row.get("source_id", "") or row.get("model_name", "")

        # Check the minimum discovery contract.  We assign higher severity to
        # missing identity fields because the row cannot be safely identified.
        for field in REQUIRED:
            if not row.get(field, "").strip():
                add_flag(
                    flags,
                    entity_id=entity_id,
                    flag_type="missing",
                    severity="high" if field in {"model_id", "model_name"} else "medium",
                    field_name=field,
                    message=f"Missing required discovery field: {field}",
                    detected_at=now,
                )

        # Anything other than explicit ``verified`` must remain outside official
        # verified aggregates.  This is a warning, not a failure: discovery is
        # expected to contain many unverified records.
        if row.get("evidence_status", "").lower() != "verified":
            add_flag(
                flags,
                entity_id=entity_id,
                flag_type="unverified",
                severity="medium",
                field_name="evidence_status",
                message="Discovery is not verified; keep outside official verified aggregates.",
                detected_at=now,
            )

        key = (
            row.get("model_name", "").strip().lower(),
            row.get("organization", "").strip().lower(),
        )
        if key != ("", ""):
            seen.setdefault(key, []).append(entity_id)

    # If the same visible name/organization is attached to more than one model
    # id, a human should inspect it.  We do not merge anything here.
    for key, ids in seen.items():
        unique_ids = set(ids)
        if len(unique_ids) > 1:
            for entity_id in unique_ids:
                add_flag(
                    flags,
                    entity_id=entity_id,
                    flag_type="identity_collision",
                    severity="medium",
                    field_name="model_name",
                    message=f"Possible identity collision for {key[0]} / {key[1]}",
                    detected_at=now,
                )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(flags)

    print(f"Atlas quality audit: {len(flags)} flags -> {OUT}")


if __name__ == "__main__":
    main()
