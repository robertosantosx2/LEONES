#!/usr/bin/env python3
"""Forgejo-compatible discovery adapter.

Works with public Forgejo APIs, including federated instances such as
Codeberg and other registry entries. Authentication is optional; public
search is intentionally rate-aware and keeps raw evidence URLs.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = "LEONES-Atlas-Prospection/1.0"


def request_json(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    token = os.getenv("FORGE_TOKEN")
    if token:
        req.add_header("Authorization", "token " + token)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), response.status


def discover(base_url: str, query: str, limit: int = 20):
    base = base_url.rstrip("/")
    url = base + "/api/v1/repos/search?" + urllib.parse.urlencode({"q": query, "limit": limit})
    data, status = request_json(url)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for item in data.get("data", []):
        html = item.get("html_url") or item.get("clone_url") or ""
        rows.append({
            "type": "software",
            "name": item.get("full_name") or item.get("name", ""),
            "url": html,
            "description": item.get("description") or "",
            "source": "forgejo",
            "source_url": base,
            "evidence_url": html,
            "license": "",
            "license_status": "unvalidated",
            "observed_at": now,
            "query": query,
            "publication_status": "discovered",
        })
    return rows, status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--output", default="data/prospection/live_discoveries.ndjson")
    p.add_argument("--limit", type=int, default=20)
    args = p.parse_args()

    rows, status = discover(args.base_url, args.query, args.limit)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps({"source": "forgejo", "base_url": args.base_url, "query": args.query, "status": status, "count": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
