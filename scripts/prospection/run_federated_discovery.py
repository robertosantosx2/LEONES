#!/usr/bin/env python3
"""Run registry-driven discovery against queryable public forge instances.

Discovery is evidence collection. Unsupported platforms are explicitly reported
and are never counted as successful queries.
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "LEONES-Atlas-Prospection/2.1"
QUERIES = ["LLM", "inference", "agent", "MCP", "model", "AI"]

TARGETS = {
    "gitlab": ("gitlab", "https://gitlab.com"),
    "framagit": ("gitlab", "https://framagit.org"),
    "gnome-gitlab": ("gitlab", "https://gitlab.gnome.org"),
    "kde-invent": ("gitlab", "https://invent.kde.org"),
    "freedesktop-gitlab": ("gitlab", "https://gitlab.freedesktop.org"),
    "codeberg": ("forgejo", "https://codeberg.org"),
    "disroot-forge": ("forgejo", "https://forge.disroot.org"),
    "notabug": ("forgejo", "https://notabug.org"),
    "pagure": ("pagure", "https://pagure.io"),
}

UNSUPPORTED = {
    "sourcehut": "search API needs authentication; no token supplied",
    "srht": "search API needs authentication; no token supplied",
    "gnu-savannah": "no compatible public search API adapter",
    "forgejo-network": "requires discovery of concrete Forgejo instances",
    "forgejo": "platform site, not a repository instance",
    "gitea": "platform site; concrete instances require discovery",
    "gitlab-ce": "platform site; concrete instances require discovery",
    "gogs": "platform site; concrete instances require discovery",
    "onedev": "platform site; concrete instances require discovery",
    "kallithea": "platform site; concrete instances require discovery",
    "phorge": "no public search adapter enabled",
    "fossil": "no common public search API",
    "rhodecode": "platform site; concrete instances require discovery",
    "cgit": "instance-specific crawling required",
    "gitbucket": "project site; concrete instances require discovery",
}


def get(url: str, source_id: str | None = None, adapter: str | None = None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})

    # Never send the GitHub Actions token to another service. GitLab instances
    # can optionally use their own source-specific token.
    token_env = {
        "gitlab": {
            "gitlab": "LEONES_GITLAB_TOKEN",
            "gnome-gitlab": "LEONES_GNOME_GITLAB_TOKEN",
            "freedesktop-gitlab": "LEONES_FREEDESKTOP_GITLAB_TOKEN",
            "framagit": "LEONES_FRAMAGIT_TOKEN",
        }
    }.get(adapter or "", {}).get(source_id or "")
    token = os.getenv(token_env) if token_env else None
    if token and adapter == "gitlab":
        req.add_header("PRIVATE-TOKEN", token)

    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8")), response.status


def normalize(source_id: str, adapter: str, base: str, item: dict, query: str, now: str):
    url = item.get("web_url") or item.get("html_url") or ""
    name = item.get("path_with_namespace") or item.get("full_name") or item.get("name") or ""
    return {
        "type": "software",
        "name": name,
        "url": url,
        "description": item.get("description") or "",
        "source": source_id,
        "source_url": base,
        "evidence_url": url,
        "license": "",
        "license_status": "unvalidated",
        "observed_at": now,
        "query": query,
        "publication_status": "discovered",
        "provenance": {"adapter": adapter, "source_id": source_id},
    }


def search_gitlab(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/v4/projects?" + urllib.parse.urlencode({"search": query, "order_by": "last_activity_at", "sort": "desc", "per_page": 20})
    data, status = get(url, source_id, "gitlab")
    now = datetime.now(timezone.utc).isoformat()
    return [normalize(source_id, "gitlab", base, x, query, now) for x in data], status


def search_forgejo(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/v1/repos/search?" + urllib.parse.urlencode({"q": query, "limit": 20})
    data, status = get(url, source_id, "forgejo")
    now = datetime.now(timezone.utc).isoformat()
    items = data.get("data", []) if isinstance(data, dict) else []
    return [normalize(source_id, "forgejo", base, x, query, now) for x in items], status


def search_pagure(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/0/projects?" + urllib.parse.urlencode({"pattern": query})
    data, status = get(url, source_id, "pagure")
    now = datetime.now(timezone.utc).isoformat()
    items = data if isinstance(data, list) else data.get("projects", [])
    return [normalize(source_id, "pagure", base, x, query, now) for x in items[:20]], status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="scripts/prospection/sources_registry.json")
    p.add_argument("--output", default="data/prospection/federated_discoveries.ndjson")
    p.add_argument("--queries", type=int, default=2)
    args = p.parse_args()

    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    ids = [x["id"] for x in registry.get("sources", [])]
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    unique = {}
    stats = Counter()
    errors = []

    with out.open("w", encoding="utf-8") as handle:
        for source_id in ids:
            if source_id in UNSUPPORTED:
                errors.append({"source_id": source_id, "status": "unsupported", "reason": UNSUPPORTED[source_id]})
                continue
            target = TARGETS.get(source_id)
            if not target:
                errors.append({"source_id": source_id, "status": "no_adapter", "reason": "No concrete public instance configured"})
                continue
            adapter, base = target
            fn = {"gitlab": search_gitlab, "forgejo": search_forgejo, "pagure": search_pagure}[adapter]
            for query in QUERIES[: args.queries]:
                try:
                    found, status = fn(source_id, base, query)
                    for row in found:
                        key = row["url"] or f"{source_id}:{row['name']}"
                        unique[key] = row
                    stats[source_id] += len(found)
                except Exception as exc:
                    errors.append({"source_id": source_id, "query": query, "status": "error", "error_type": type(exc).__name__, "message": str(exc)[:300]})

        for row in unique.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_in_registry": len(ids),
        "sources_successfully_queried": sorted(stats),
        "raw_results_by_source": dict(stats),
        "unique_discoveries": len(unique),
        "errors_or_unsupported": errors,
        "error_count": len(errors),
        "output": str(out),
        "note": "Unsupported sources are explicit; they are not counted as successful discovery. License Gate remains independent.",
    }
    (out.parent / "federated_discovery_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
