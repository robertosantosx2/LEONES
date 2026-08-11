#!/usr/bin/env python3
"""Aggregate canonical LEONES result JSON files.

One job: statistics. This script does not benchmark, publish, or generate
individual reports. It consumes the same structured result produced by the
measurement pipeline.

By default it scans ``results/`` recursively. A valid result must contain
``schema_version`` and one of the LEONES evidence states. Rejected results are
kept in status counts but excluded from official performance aggregates.

Usage:
    python3 scripts/leones-stats.py
    python3 scripts/leones-stats.py --root results --output web/data/stats.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

VALID_STATUSES = {"reported", "reproducible", "verified", "rejected"}


def load_results(root: Path, exclude_demo: bool) -> list[dict]:
    results: list[dict] = []
    if not root.exists():
        return results
    for path in root.rglob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if "schema_version" not in data or data.get("status") not in VALID_STATUSES:
            continue
        if exclude_demo and data.get("demo") is True:
            continue
        results.append(data)
    return results


def aggregate(results: list[dict]) -> dict:
    official = [r for r in results if r.get("status") != "rejected"]
    verified = [r for r in results if r.get("status") == "verified"]
    statuses = Counter(r.get("status") for r in results)
    profiles = Counter()
    ram = Counter()
    speeds: list[float] = []
    lotb: dict[str, Counter] = defaultdict(Counter)

    for result in official:
        hardware = result.get("hardware", {})
        if hardware.get("profile"):
            profiles[str(hardware["profile"])] += 1
        if hardware.get("ram_gb") is not None:
            ram[str(hardware["ram_gb"])] += 1

        speed = result.get("inference", {}).get("generation_tokens_per_second")
        if isinstance(speed, (int, float)):
            speeds.append(float(speed))

        for code, task in result.get("lotb", {}).items():
            if isinstance(task, dict):
                lotb[code][str(task.get("status", "unknown"))] += 1

    return {
        "schema_version": "1.0",
        "result_count": len(results),
        "official_count": len(official),
        "verified_count": len(verified),
        "status_counts": dict(statuses),
        "hardware_profiles": dict(profiles),
        "ram_gb": dict(ram),
        "generation_tokens_per_second": {
            "count": len(speeds),
            "min": min(speeds) if speeds else None,
            "max": max(speeds) if speeds else None,
            "average": round(sum(speeds) / len(speeds), 3) if speeds else None,
            "at_least_10": sum(x >= 10 for x in speeds),
            "at_least_100": sum(x >= 100 for x in speeds),
        },
        "lotb": {code: dict(counts) for code, counts in sorted(lotb.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate LEONES result JSON files")
    parser.add_argument("--root", default="results", help="Directory containing result JSON files")
    parser.add_argument("--output", default="web/data/stats.json", help="Statistics JSON output")
    parser.add_argument("--exclude-demo", action="store_true", help="Ignore result files marked demo=true")
    args = parser.parse_args()

    results = load_results(Path(args.root), args.exclude_demo)
    output = aggregate(results)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
