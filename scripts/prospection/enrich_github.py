#!/usr/bin/env python3
"""Enrich GitHub discoveries and preserve evidence from other public forges."""
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
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "LEONES-Atlas-Prospection/1.2",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")), {
                "status": r.status,
                "rate_limit_remaining": r.headers.get("X-RateLimit-Remaining"),
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
            message = payload.get("message", "")
        except Exception:
            message = body[:300]
        return {"_error": f"HTTP {e.code}", "_status": e.code, "_message": message}, {
            "status": e.code,
            "rate_limit_remaining": e.headers.get("X-RateLimit-Remaining"),
            "rate_limit_reset": e.headers.get("X-RateLimit-Reset"),
        }
    except Exception as e:
        return {"_error": type(e).__name__, "_message": str(e)[:300]}, {}


def repo_name(url: str):
    parts = url.rstrip("/").split("github.com/", 1)
    if len(parts) != 2:
        return None
    bits = parts[1].split("/")
    return f"{bits[0]}/{bits[1]}" if len(bits) >= 2 else None


def is_github(url: str) -> bool:
    return "github.com/" in (url or "").lower()


def error_record(payload, meta):
    return {
        "status": "error",
        "http_status": payload.get("_status") or meta.get("status"),
        "error_type": payload.get("_error", "github_api"),
        "message": payload.get("_message", "unknown error"),
        "rate_limit_remaining": meta.get("rate_limit_remaining"),
        "rate_limit_reset": meta.get("rate_limit_reset"),
    }


def enrich(item):
    url = item.get("url", "")
    if not is_github(url):
        item["enrichment"] = {
            "status": "skipped_non_github",
            "reason": "Evidence preserved for source-specific enrichment; no GitHub API call made.",
            "source": item.get("source"),
            "evidence_url": item.get("evidence_url") or url,
        }
        return item

    full = repo_name(url)
    if not full:
        item["enrichment"] = {"status": "error", "error_type": "invalid_repository_url"}
        return item

    repo, meta = request_json(f"{API}/repos/{full}")
    if repo.get("_error"):
        item["enrichment"] = error_record(repo, meta)
        return item

    license_obj = repo.get("license") or {}
    topics, _ = request_json(f"{API}/repos/{full}/topics")
    readme, _ = request_json(f"{API}/repos/{full}/readme")
    readme_text = ""
    if isinstance(readme, dict) and readme.get("content"):
        try:
            readme_text = base64.b64decode(readme["content"]).decode("utf-8", errors="replace")
        except Exception:
            pass

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
        "rate_limit_remaining": meta.get("rate_limit_remaining"),
    }
    return item


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", default="data/prospection/live_discoveries.ndjson")
    p.add_argument("--output", default="data/prospection/enriched_discoveries.ndjson")
    p.add_argument("--max", type=int, default=0)
    p.add_argument("--delay", type=float, default=0.15)
    args = p.parse_args()

    source, destination = Path(args.input), Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    seen, diagnostics = set(), []
    total = ok = skipped = errors = 0

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
            enrichment = item.get("enrichment", {})
            if enrichment.get("status") == "ok":
                ok += 1
            elif enrichment.get("status") == "skipped_non_github":
                skipped += 1
            else:
                errors += 1
                if len(diagnostics) < 10:
                    diagnostics.append({
                        "repository": repo_name(item.get("url", "")),
                        "status": enrichment.get("http_status"),
                        "error_type": enrichment.get("error_type"),
                        "message": enrichment.get("message"),
                        "rate_limit_remaining": enrichment.get("rate_limit_remaining"),
                    })
            dst.write(json.dumps(item, ensure_ascii=False) + "\n")
            time.sleep(args.delay)

    report = {
        "input": str(source),
        "output": str(destination),
        "repositories_processed": total,
        "enriched_ok": ok,
        "non_github_preserved": skipped,
        "errors": errors,
        "github_token_used": bool(os.environ.get("GITHUB_TOKEN")),
        "diagnostics": diagnostics,
        "note": "GitHub repositories are enriched through the GitHub API. Non-GitHub evidence is preserved for source-specific enrichment and is not treated as an error.",
    }
    Path("data/prospection/enrichment_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
