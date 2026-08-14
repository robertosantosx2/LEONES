#!/usr/bin/env python3
"""Run registry-driven discovery against queryable public sources.

Discovery is evidence collection. Unsupported sources are explicitly reported
and are never counted as successful queries. Source-specific credentials are
never shared between services.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "LEONES-Atlas-Prospection/2.2"
QUERIES = ["LLM", "inference", "agent", "MCP", "model", "AI"]

TARGETS = {
    "gitlab": ("gitlab", "https://gitlab.com"),
    "framagit": ("gitlab", "https://framagit.org"),
    "codeberg": ("forgejo", "https://codeberg.org"),
    "disroot-forge": ("forgejo", "https://forge.disroot.org"),
    "notabug": ("forgejo", "https://notabug.org"),
    "pagure": ("pagure", "https://pagure.io"),
    "huggingface": ("huggingface-models", "https://huggingface.co"),
    "huggingface-papers": ("huggingface-papers", "https://huggingface.co"),
    "gnu-savannah": ("savannah", "https://savannah.gnu.org"),
}

UNSUPPORTED = {
    "sourcehut": "search API needs authentication; no token supplied",
    "srht": "search API needs authentication; no token supplied",
    "forgejo-network": "requires discovery of concrete Forgejo instances; set LEONES_FORGEJO_INSTANCES to a comma-separated list",
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
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"})
    token_env = {
        "gitlab": {
            "gitlab": "LEONES_GITLAB_TOKEN",
            "framagit": "LEONES_FRAMAGIT_TOKEN",
        },
        "huggingface-models": {"huggingface": "HF_TOKEN"},
        "huggingface-papers": {"huggingface-papers": "HF_TOKEN"},
        "forgejo": {},
    }.get(adapter or "", {}).get(source_id or "")
    token = os.getenv(token_env) if token_env else None
    if token and adapter == "gitlab":
        req.add_header("PRIVATE-TOKEN", token)
    elif token and adapter.startswith("huggingface"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as response:
        return response.read().decode("utf-8"), response.status


def normalize(source_id: str, adapter: str, base: str, item: dict, query: str, now: str, kind: str = "software"):
    url = item.get("web_url") or item.get("html_url") or item.get("url") or ""
    name = item.get("path_with_namespace") or item.get("full_name") or item.get("id") or item.get("name") or ""
    return {
        "type": kind,
        "name": str(name),
        "url": url,
        "description": item.get("description") or item.get("summary") or "",
        "source": source_id,
        "source_url": base,
        "evidence_url": url,
        "license": item.get("license") or "",
        "license_status": "unvalidated",
        "observed_at": now,
        "query": query,
        "publication_status": "discovered",
        "provenance": {"adapter": adapter, "source_id": source_id},
    }


def search_gitlab(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/v4/projects?" + urllib.parse.urlencode({"search": query, "order_by": "last_activity_at", "sort": "desc", "per_page": 20})
    raw, status = get(url, source_id, "gitlab")
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    return [normalize(source_id, "gitlab", base, x, query, now) for x in data], status


def search_forgejo(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/v1/repos/search?" + urllib.parse.urlencode({"q": query, "limit": 20})
    raw, status = get(url, source_id, "forgejo")
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    items = data.get("data", []) if isinstance(data, dict) else []
    return [normalize(source_id, "forgejo", base, x, query, now) for x in items], status


def search_pagure(source_id: str, base: str, query: str):
    url = base.rstrip("/") + "/api/0/projects?" + urllib.parse.urlencode({"pattern": query})
    raw, status = get(url, source_id, "pagure")
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    items = data if isinstance(data, list) else data.get("projects", [])
    return [normalize(source_id, "pagure", base, x, query, now) for x in items[:20]], status


def search_huggingface_models(source_id: str, base: str, query: str):
    url = base + "/api/models?" + urllib.parse.urlencode({"search": query, "limit": 20, "sort": "lastModified", "direction": -1})
    raw, status = get(url, source_id, "huggingface-models")
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for x in data if isinstance(data, list) else []:
        repo_id = x.get("id", "")
        rows.append(normalize(source_id, "huggingface-models", base, {"id": repo_id, "url": f"{base}/" + repo_id, "description": "", "license": x.get("cardData", {}).get("license", "")}, query, now, "model"))
    return rows, status


def search_huggingface_papers(source_id: str, base: str, query: str):
    # The public Daily Papers feed is paginated; filtering is performed locally.
    url = base + "/api/daily_papers?" + urllib.parse.urlencode({"limit": 100, "offset": 0})
    raw, status = get(url, source_id, "huggingface-papers")
    data = json.loads(raw)
    now = datetime.now(timezone.utc).isoformat()
    items = data.get("recentPapers", data.get("papers", [])) if isinstance(data, dict) else data
    tokens = [t.lower() for t in query.split() if t]
    rows = []
    for x in items or []:
        text = json.dumps(x, ensure_ascii=False).lower()
        if tokens and not all(t in text for t in tokens):
            continue
        paper = x.get("paper", x) if isinstance(x, dict) else {}
        paper_id = paper.get("id") or paper.get("paperId") or x.get("id", "")
        title = paper.get("title") or x.get("title") or paper_id
        url = f"{base}/papers/{paper_id}" if paper_id else base + "/papers"
        rows.append(normalize(source_id, "huggingface-papers", base, {"id": title, "url": url, "summary": paper.get("summary", "")}, query, now, "paper"))
    return rows[:20], status


class SavannahParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.capture = False
        self.href = ""
        self.text = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs = dict(attrs)
            href = attrs.get("href", "")
            if "/projects/" in href or "group_id=" in href:
                self.capture = True; self.href = href; self.text = []
    def handle_data(self, data):
        if self.capture: self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.capture:
            label = " ".join("".join(self.text).split())
            self.links.append((self.href, label)); self.capture = False


def search_savannah(source_id: str, base: str, query: str):
    url = base + "/search/" + urllib.parse.quote(query) + "/"
    raw, status = get(url, source_id, "savannah")
    parser = SavannahParser(); parser.feed(raw)
    now = datetime.now(timezone.utc).isoformat()
    seen = set(); rows = []
    for href, label in parser.links:
        if not label or href in seen: continue
        seen.add(href)
        if href.startswith("/"): href = base + href
        rows.append(normalize(source_id, "savannah", base, {"id": label, "url": urllib.parse.urljoin(base, href)}, query, now))
        if len(rows) >= 20: break
    return rows, status


def forgejo_network_instances():
    raw = os.getenv("LEONES_FORGEJO_INSTANCES", "")
    return [x.strip().rstrip("/") for x in raw.split(",") if x.strip()]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", default="scripts/prospection/sources_registry.json")
    p.add_argument("--output", default="data/prospection/federated_discoveries.ndjson")
    p.add_argument("--queries", type=int, default=2)
    args = p.parse_args()

    registry = json.loads(Path(args.registry).read_text(encoding="utf-8"))
    ids = [x["id"] for x in registry.get("sources", [])]
    out = Path(args.output); out.parent.mkdir(parents=True, exist_ok=True)
    unique = {}; stats = Counter(); errors = []

    # Optional concrete Forgejo instances can be added without changing code.
    instances = forgejo_network_instances()
    if instances:
        for base in instances:
            sid = "forgejo-instance:" + urllib.parse.urlparse(base).netloc
            for query in QUERIES[:args.queries]:
                try:
                    found, _ = search_forgejo(sid, base, query)
                    for row in found: unique[row["url"] or f"{sid}:{row['name']}"] = row
                    stats[sid] += len(found)
                except Exception as exc:
                    errors.append({"source_id": sid, "query": query, "status": "error", "error_type": type(exc).__name__, "message": str(exc)[:300]})

    for source_id in ids:
        if source_id == "forgejo-network" and instances:
            continue
        if source_id in UNSUPPORTED:
            errors.append({"source_id": source_id, "status": "unsupported", "reason": UNSUPPORTED[source_id]})
            continue
        target = TARGETS.get(source_id)
        if not target:
            errors.append({"source_id": source_id, "status": "no_adapter", "reason": "No concrete public instance configured"})
            continue
        adapter, base = target
        fn = {
            "gitlab": search_gitlab,
            "forgejo": search_forgejo,
            "pagure": search_pagure,
            "huggingface-models": search_huggingface_models,
            "huggingface-papers": search_huggingface_papers,
            "savannah": search_savannah,
        }[adapter]
        for query in QUERIES[: args.queries]:
            try:
                found, status = fn(source_id, base, query)
                for row in found:
                    key = row["url"] or f"{source_id}:{row['name']}"
                    unique[key] = row
                stats[source_id] += len(found)
            except Exception as exc:
                errors.append({"source_id": source_id, "query": query, "status": "error", "error_type": type(exc).__name__, "message": str(exc)[:300]})

    with out.open("w", encoding="utf-8") as handle:
        for row in unique.values(): handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources_in_registry": len(ids),
        "sources_successfully_queried": sorted(stats),
        "raw_results_by_source": dict(stats),
        "unique_discoveries": len(unique),
        "errors_or_unsupported": errors,
        "error_count": len(errors),
        "output": str(out),
        "note": "Unsupported sources are explicit; License Gate remains independent.",
    }
    (out.parent / "federated_discovery_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
