#!/usr/bin/env python3
"""Enrich GitHub discoveries with repository metadata and README evidence.

The original discovery file is never modified. This produces a separate NDJSON
stream suitable for classification and later license review.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.github.com"


def request_json(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "LEONES-Atlas-Prospection/1.0",
        },
    )
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}", "_status": e.code}
    except Exception as e:
        return {"_error": str(e)}


def repo_name(url: str):
    parts = url.rstrip("/").split("github.com/", 1)
    if len(parts) != 2:
        return None
    bits = parts[1].split("/")
    if len(bits) < 2:
        return None
    return f"{bits[0]}/{bits[1]}"


def enrich(item):
    full = repo_name(item.get("url", ""))
    item["enrichment"] = {"status": "unavailable"}
    if not full:
        return item

    repo = request_json(f"{API}/repos/{full}")
    if repo.get("_error"):
        item["enrichment"] = {"status": "error", **repo}
        return item

    license_obj = repo.get("license") or {}
    topics = request_json(f"{API}/repos/{full}/topics")
    readme = request_json(f"{API}/repos/{full}/readme")

    readme_text = ""
    if isinstance(readme, dict) and readme.get("content"):
        try:
            readme_text = base64.b64decode(
                readme["content"]
            ).decode("utf-8", errors="replace")
        except Exception:
            readme_text = ""

    item["description"] = repo.get("description") or item.get("description")
    item["enrichment"] = {
        "status": "ok",
        "repository_id": repo.get("id"),
        "default_branch": repo.get("default_branch"),
        "created_at": repo.get("created_at"),
        "updated_at": repo.get("updated_at"),
        "pushed_at": repo.get("pushed_at"),
        "stargazers_count": repo.get("stargazers_count"),
        "forks_count": repo.get("forks_count"),
        "open_issues_count": repo.get("open_issues_count"),
        "language": repo.get("language"),
        "languages_url": repo.get("languages_url"),
        "topics": topics.get("names", []) if isinstance(topics, dict) else [],
        "license": license_obj.get("spdx_id") or license_obj.get("name"),
        "license_url": license_obj.get("url"),
        "license_key": license_obj.get("key"),
        "html_url": repo.get("html_url"),
        "homepage": repo.get("homepage"),
        "readme_url": readme.get("html_url") if isinstance(readme, dict) else None,
        "readme_excerpt": readme_text[:12000],
    }
    return item


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="data/prospection/live_discoveries.ndjson")
    p.add_argument("--output", default="data/prospection/enriched_discoveries.ndjson")
    p.add_argument("--max", type=int, default=0, help="maximum unique repositories; 0 = all")
    p.add_argument("--delay", type=float, default=0.15)
    args = p.parse_args()

    source = Path(args.input)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)

    seen = set()
    total = 0
    ok = 0
    errors = 0

    with source.open(encoding="utf-8") as src, destination.open("w", encoding="utf-8") as dst:
        for line in src:
            if not line.strip():
                continue
            item = json.loads(line)
            key = (item.get("source", ""), item.get("url", "").rstrip("/").lower())
            if key in seen:
                continue
            if args.max and len(seen) >= args.max:
                break
            seen.add(key)
            total += 1
            item = enrich(item)
            if item.get("enrichment", {}).get("status") == "ok":
                ok += 1
            else:
                errors += 1
            dst.write(json.dumps(item, ensure_ascii=False) + "\n")
            dst.flush()
            time.sleep(args.delay)

    report = {
        "input": str(source),
        "output": str(destination),
        "repositories_processed": total,
        "enriched_ok": ok,
        "errors": errors,
        "github_token_used": bool(os.environ.get("GITHUB_TOKEN")),
        "note": "Enrichment is evidence collection only; it does not publish to Atlas or approve licenses.",
    }
    Path("data/prospection/enrichment_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
