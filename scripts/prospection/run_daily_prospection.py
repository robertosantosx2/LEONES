#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REGISTRY = ROOT / "scripts/prospection/sources_registry.json"
PLAN = ROOT / "scripts/prospection/adapters/source_query_plan.json"
OUT = ROOT / "data/prospection"

CATEGORY_QUERIES = {
    "models": [
        "LLM",
        "language model",
        "vision language model",
        "embedding model",
        "reranker",
        "multimodal model",
    ],
    "runtimes": [
        "LLM inference",
        "inference runtime",
        "model serving",
        "local inference",
        "quantization",
    ],
    "agents": [
        "AI agent",
        "agent framework",
        "tool calling",
        "MCP agent",
        "autonomous agent",
    ],
    "skills": [
        "AI skill",
        "MCP server",
        "AI tool",
        "agent tool",
        "plugin",
    ],
    "harnesses": [
        "evaluation harness",
        "benchmark harness",
        "agent harness",
        "LLM evaluation",
        "agent testing",
    ],
    "hardware": [
        "AI accelerator",
        "CPU inference",
        "GPU inference",
        "NPU inference",
        "AI hardware",
        "edge AI",
    ],
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--registry",
        default=str(REGISTRY),
    )

    parser.add_argument(
        "--plan",
        default=str(PLAN),
    )

    parser.add_argument(
        "--output",
        default=str(
            OUT / "source_discovery_plan.ndjson"
        ),
    )

    args = parser.parse_args()

    registry = load_json(Path(args.registry))
    plan = load_json(Path(args.plan))

    sources = {
        item["id"]: item
        for item in registry.get("sources", [])
    }

    now = datetime.now(timezone.utc).isoformat()

    destination = Path(args.output)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = []

    for family in plan.get("families", []):

        for source_id in family.get(
            "sources", []
        ):

            source = sources.get(source_id)

            if not source:
                continue

            for category, queries in CATEGORY_QUERIES.items():

                family_queries = list(
                    dict.fromkeys(
                        family.get("queries", [])
                        + queries
                    )
                )

                for query in family_queries:

                    rows.append(
                        {
                            "observed_at": now,
                            "source": source_id,
                            "source_url": source.get(
                                "url", ""
                            ),
                            "source_kind": source.get(
                                "kind", ""
                            ),
                            "priority": source.get(
                                "priority",
                                "medium",
                            ),
                            "family": family.get(
                                "id", ""
                            ),
                            "category": category,
                            "adapter": family.get(
                                "adapter", ""
                            ),
                            "query": query,

                            "status": "planned",

                            "license_status":
                                "unvalidated",

                            "publication_status":
                                "discovered",

                            "provenance": {
                                "registry_id":
                                    source_id,

                                "registry_url":
                                    source.get(
                                        "url", ""
                                    ),

                                "query_plan":
                                    family.get(
                                        "id", ""
                                    ),
                            },
                        }
                    )

    with destination.open(
        "w",
        encoding="utf-8",
    ) as handle:

        for row in rows:

            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                )
                + "\n"
            )

    report = OUT / "daily_source_report.json"

    report.write_text(
        json.dumps(
            {
                "generated_at": now,
                "status": "planned",
                "sources_in_registry":
                    len(sources),
                "discovery_queries":
                    len(rows),

                "categories": list(
                    CATEGORY_QUERIES
                ),

                "license_policy":
                    "license_gate_before_publication",

                "note":
                    "Query planning is separate "
                    "from live discovery and Atlas "
                    "publication.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "sources": len(sources),
                "queries": len(rows),
                "output": str(
                    destination
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
