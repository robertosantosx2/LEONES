#!/usr/bin/env python3
"""Discover external estimate sources.

This script deliberately does NOT validate claims and does NOT write Atlas.
It fetches each URL listed in config/external_sources.txt and records only
basic discovery metadata. Human review is required before publication.
"""

import argparse
import json
import urllib.request
from datetime import date
from pathlib import Path


def discover(source_file: Path, output: Path) -> None:
    records = []
    for raw in source_file.read_text(encoding="utf-8").splitlines():
        url = raw.strip()
        if not url or url.startswith("#"):
            continue
        record = {
            "observed_at": date.today().isoformat(),
            "source_url": url,
            "status": "external-unvalidated",
        }
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "LEONES-external-discovery/0.1"})
            with urllib.request.urlopen(request, timeout=20) as response:
                record["http_status"] = response.status
                record["content_type"] = response.headers.get("Content-Type", "")
        except Exception as exc:
            record["error"] = type(exc).__name__
        records.append(record)

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as target:
        for record in records:
            target.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discover LEONES external estimate sources.")
    parser.add_argument("--sources", default="config/external_sources.txt")
    parser.add_argument("--output", default="data/external_discovery.jsonl")
    args = parser.parse_args()
    discover(Path(args.sources), Path(args.output))
