"""Daily discovery of open AI ecosystem resources.

One responsibility: read a small, explicit source list and record discovered
items as external, unvalidated information. It never promotes findings to
Leones Atlas and never changes Router decisions.

The source list is deliberately simple: one URL per line. For each URL we
store the discovery date, source and page title when available. Rich semantic
classification is left for later review.
"""

from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import date
from pathlib import Path


def discover(source_file: Path, output_file: Path) -> int:
    """Probe configured sources and append discovery records."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    for raw in source_file.read_text(encoding="utf-8").splitlines():
        url = raw.strip()
        if not url or url.startswith("#"):
            continue
        record = {
            "discovered_at": date.today().isoformat(),
            "url": url,
            "status": "external-unvalidated",
        }
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "LEONES-Prospector/0.1"})
            with urllib.request.urlopen(request, timeout=15) as response:
                record["http_status"] = response.status
        except Exception as exc:  # discovery must not stop because one source failed
            record["error"] = type(exc).__name__
        with output_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LEONES daily Prospector discovery.")
    parser.add_argument("--sources", type=Path, default=Path("config/prospector_sources.txt"))
    parser.add_argument("--output", type=Path, default=Path("data/prospector/discoveries.jsonl"))
    args = parser.parse_args()
    print(f"Discovered {discover(args.sources, args.output)} sources")


if __name__ == "__main__":
    main()
