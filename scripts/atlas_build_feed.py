#!/usr/bin/env python3
"""Build a normalized Atlas feed from LEONES daily prospection outputs.

This is deliberately conservative: discovery records are copied into the feed,
but verification state is preserved and no JGB/performance values are invented.
"""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROSPECTION = ROOT / "data" / "prospection"
OUT = PROSPECTION / "atlas_feed.csv"

FIELDS = [
    "source_file",
    "source_id",
    "model_id",
    "model_name",
    "organization",
    "release_date",
    "source_url",
    "license",
    "weights_url",
    "code_url",
    "runtime",
    "format",
    "quantization",
    "hardware_id",
    "workload",
    "jgb_level",
    "jgb_confidence",
    "quality_score",
    "tokens_per_second",
    "estimated_memory_gb",
    "context_tokens",
    "evidence_status",
    "notes",
]

ALIASES = {
    "id": "source_id",
    "model": "model_id",
    "name": "model_name",
    "url": "source_url",
    "date": "release_date",
    "license_name": "license",
    "weights": "weights_url",
    "code": "code_url",
}


def normalize(row: dict[str, str], source_file: str) -> dict[str, str]:
    out = {field: "" for field in FIELDS}
    out["source_file"] = source_file
    for key, value in row.items():
        target = ALIASES.get(key.strip(), key.strip())
        if target in out:
            out[target] = (value or "").strip()
    if not out["evidence_status"]:
        out["evidence_status"] = "discovered"
    return out


def main() -> None:
    records: list[dict[str, str]] = []
    for path in sorted(PROSPECTION.glob("*.csv")):
        if path.name == OUT.name:
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if not reader.fieldnames:
                continue
            for row in reader:
                records.append(normalize(row, path.name))

    # Stable de-duplication: prefer source_id, otherwise model+source URL.
    unique: dict[str, dict[str, str]] = {}
    for record in records:
        key = record["source_id"] or f"{record['model_id']}|{record['source_url']}"
        if key == "|":
            continue
        unique.setdefault(key, record)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(unique.values())

    print(f"Atlas feed: {len(unique)} records -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
