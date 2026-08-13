#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "LEONES-Atlas-Prospection/1.0"


def get(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
        },
        method="GET",
    )

    token = os.getenv("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        req.add_header("Authorization", "Bearer " + token)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), response.status


def github(query, limit=30):
    url = (
        "https://api.github.com/search/repositories?"
        + urllib.parse.urlencode(
            {
                "q": query,
                "sort": "updated",
                "order": "desc",
                "per_page": limit,
            }
        )
    )

    data, status = get(url)
    observed = datetime.now(timezone.utc).isoformat()

    rows = []

    for item in data.get("items", []):
        license_data = item.get("license") or {}

        rows.append(
            {
                "type": "software",
                "name": item.get("name", ""),
                "organization": (
                    item.get("owner") or {}
                ).get("login", ""),
                "url": item.get("html_url", ""),
                "source": "github",
                "license": license_data.get("spdx_id", ""),
                "description": item.get("description", ""),
                "evidence_url": item.get("html_url", ""),
                "observed_at": observed,
            }
        )

    return rows, status


def huggingface(query, limit=30):
    url = (
        "https://huggingface.co/api/models?"
        + urllib.parse.urlencode(
            {
                "search": query,
                "limit": limit,
                "sort": "lastModified",
                "direction": -1,
            }
        )
    )

    data, status = get(url)
    observed = datetime.now(timezone.utc).isoformat()

    rows = []

    for item in data:
        identifier = item.get("id", "")

        if not identifier:
            continue

        rows.append(
            {
                "type": "model",
                "name": identifier,
                "organization": (
                    identifier.split("/", 1)[0]
                    if "/" in identifier
                    else ""
                ),
                "url": "https://huggingface.co/" + identifier,
                "source": "huggingface",
                "license": item.get("license", ""),
                "evidence_url": "https://huggingface.co/" + identifier,
                "observed_at": observed,
            }
        )

    return rows, status


def write(rows, path):
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with destination.open("a", encoding="utf-8") as output:
        for row in rows:
            output.write(
                json.dumps(row, ensure_ascii=False) + "\n"
            )


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--output",
        default="data/prospection/live_discoveries.ndjson",
    )

    parser.add_argument(
        "--github-query",
        action="append",
        default=[
            "LLM inference",
            "LLM runtime",
            "agent framework",
        ],
    )

    parser.add_argument(
        "--hf-query",
        action="append",
        default=[
            "text-generation",
            "code-generation",
            "agents",
        ],
    )

    args = parser.parse_args()

    total = 0

    for query in args.github_query:
        rows, status = github(query)
        write(rows, args.output)

        print(
            json.dumps(
                {
                    "source": "github",
                    "query": query,
                    "status": status,
                    "count": len(rows),
                },
                ensure_ascii=False,
            )
        )

        total += len(rows)

    for query in args.hf_query:
        rows, status = huggingface(query)
        write(rows, args.output)

        print(
            json.dumps(
                {
                    "source": "huggingface",
                    "query": query,
                    "status": status,
                    "count": len(rows),
                },
                ensure_ascii=False,
            )
        )

        total += len(rows)

    print(
        json.dumps(
            {
                "total": total,
                "output": args.output,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
