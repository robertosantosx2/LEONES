#!/usr/bin/env python3
"""Execute a source-query plan against injectable adapters.

This module is intentionally transport-neutral: CI can inject API clients or
cached responses. It records failures rather than pretending a source was
queried successfully.
"""

from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--plan", default="scripts/prospection/adapters/source_query_plan.json"
    )
    ap.add_argument("--report", default="data/prospection/daily_source_report.json")
    args = ap.parse_args()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "planned",
        "families": [],
    }
    for family in plan.get("families", []):
        report["families"].append(
            {
                "id": family["id"],
                "adapter": family["adapter"],
                "sources": family["sources"],
                "queries": family["queries"],
                "status": "adapter-client-required",
            }
        )
    p = Path(args.report)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
