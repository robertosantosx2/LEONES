#!/usr/bin/env python3
"""Parallel, bounded enrichment for GitLab and Forgejo/Gitea discoveries."""

from __future__ import annotations
import argparse, base64, json, os, urllib.parse, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

UA = "LEONES-Atlas-Prospection/2.5"
LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING", "COPYING.md")


def get(url, token=None, timeout=10):
    h = {"User-Agent": UA, "Accept": "application/json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8")), r.status, None
    except urllib.error.HTTPError as e:
        return None, e.code, e.reason
    except Exception as e:
        return None, None, str(e)


def raw(url, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""


def license_from_text(text):
    t = text.lower()
    patterns = [
        (
            "Apache-2.0",
            (
                "apache license, version 2.0",
                "licensed under the apache license, version 2.0",
            ),
        ),
        ("MIT", ("permission is hereby granted, free of charge",)),
        (
            "GPL-3.0",
            (
                "gnu general public license version 3",
                "gnu general public license, version 3",
            ),
        ),
        (
            "GPL-2.0",
            (
                "gnu general public license version 2",
                "gnu general public license, version 2",
            ),
        ),
        ("AGPL-3.0", ("gnu affero general public license",)),
        ("LGPL-3.0", ("gnu lesser general public license version 3",)),
        ("LGPL-2.1", ("gnu lesser general public license version 2.1",)),
        ("MPL-2.0", ("mozilla public license, version 2.0",)),
        (
            "BSD-3-Clause",
            (
                "redistribution and use in source and binary forms",
                "neither the name of the",
            ),
        ),
        ("ISC", ("permission to use, copy, modify, and/or distribute this software",)),
    ]
    for spdx, needles in patterns:
        if any(n in t for n in needles):
            return spdx
    return ""


def host(x):
    p = urllib.parse.urlparse(x.get("source_url") or x.get("url") or "")
    return f"{p.scheme}://{p.netloc}"


def enrich_one(item):
    adapter = (item.get("provenance") or {}).get("adapter", "")
    before = item.get("license")
    try:
        if adapter == "gitlab":
            base = host(item)
            project = urllib.parse.urlparse(item.get("url", "")).path.strip("/")
            if not project:
                return item, "unchanged", False
            token = os.getenv("LEONES_GITLAB_TOKEN") or os.getenv(
                "LEONES_FRAMAGIT_TOKEN"
            )
            api = f"{base}/api/v4/projects/{urllib.parse.quote(project, safe='')}"
            repo, status, err = get(api, token)
            if status != 200 or not repo:
                item["enrichment"] = {
                    "status": "error",
                    "http_status": status,
                    "message": str(err),
                }
                return item, "error", False
            lic = (
                (repo.get("license") or {}).get("key")
                or (repo.get("license") or {}).get("name")
                or ""
            )
            item["description"] = repo.get("description") or item.get("description")
            item["enrichment"] = {
                "status": "ok",
                "platform": "gitlab",
                "project_id": repo.get("id"),
                "default_branch": repo.get("default_branch"),
                "last_activity_at": repo.get("last_activity_at"),
                "license": lic,
                "license_url": (repo.get("license") or {}).get("url"),
                "web_url": repo.get("web_url"),
            }
            if lic:
                item["license"] = lic
                item["license_status"] = "declared_from_gitlab"
            else:
                branch = repo.get("default_branch") or "main"
                for name in LICENSE_FILES:
                    data, st, _ = get(
                        f"{base}/api/v4/projects/{repo['id']}/repository/files/{urllib.parse.quote(name, safe='')}?ref={urllib.parse.quote(branch)}",
                        token,
                        timeout=7,
                    )
                    if st == 200 and data and data.get("content"):
                        try:
                            text = base64.b64decode(data["content"]).decode(
                                "utf-8", errors="replace"
                            )
                        except Exception:
                            text = ""
                        found = license_from_text(text)
                        if found:
                            item["license"] = found
                            item["license_status"] = "evidence_from_gitlab_license_file"
                            item["enrichment"]["license_file"] = name
                            break
            return (
                item,
                "gitlab",
                bool(item.get("license") and item.get("license") != before),
            )
        if adapter == "forgejo":
            base = host(item)
            parts = (
                urllib.parse.urlparse(item.get("url", "")).path.strip("/").split("/")
            )
            if len(parts) < 2:
                return item, "unchanged", False
            owner, repo = parts[:2]
            data, status, err = get(
                f"{base}/api/v1/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
            )
            if status != 200 or not data:
                item["enrichment"] = {
                    "status": "error",
                    "http_status": status,
                    "message": str(err),
                }
                return item, "error", False
            lic = (
                (data.get("license") or {}).get("spdx_id")
                or (data.get("license") or {}).get("name")
                or data.get("license")
                or ""
            )
            item["description"] = data.get("description") or item.get("description")
            item["enrichment"] = {
                "status": "ok",
                "platform": "forgejo-gitea",
                "repository_id": data.get("id"),
                "default_branch": data.get("default_branch"),
                "updated_at": data.get("updated_at"),
                "license": lic,
                "html_url": data.get("html_url"),
            }
            if lic:
                item["license"] = lic
                item["license_status"] = "declared_from_forgejo"
            else:
                branch = data.get("default_branch") or "main"
                for name in LICENSE_FILES:
                    text = raw(
                        f"{base}/{owner}/{repo}/raw/branch/{urllib.parse.quote(branch)}/{urllib.parse.quote(name)}"
                    )
                    found = license_from_text(text)
                    if found:
                        item["license"] = found
                        item["license_status"] = "evidence_from_forge_license_file"
                        item["enrichment"]["license_file"] = name
                        break
            return (
                item,
                "forgejo",
                bool(item.get("license") and item.get("license") != before),
            )
        return item, "unchanged", False
    except Exception as e:
        item["enrichment"] = {
            "status": "error",
            "http_status": None,
            "message": str(e)[:300],
        }
        return item, "error", False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/prospection/enriched_discoveries.ndjson")
    ap.add_argument("--output", default="data/prospection/enriched_discoveries.ndjson")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--max-items", type=int, default=500)
    args = ap.parse_args()
    src = Path(args.input)
    out = Path(args.output)
    items = []
    with src.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))
    if len(items) > args.max_items:
        items = items[: args.max_items]
    results = [None] * len(items)
    counts = {
        "gitlab": 0,
        "forgejo": 0,
        "unchanged": 0,
        "errors": 0,
        "licenses_found": 0,
    }
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(enrich_one, x): i for i, x in enumerate(items)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                x, kind, found = fut.result()
            except Exception as e:
                x = items[i]
                kind = "error"
                found = False
                x["enrichment"] = {"status": "error", "message": str(e)}
            results[i] = x
            counts[kind] = counts.get(kind, 0) + 1
            if found:
                counts["licenses_found"] += 1
    tmp = out.with_suffix(".tmp.ndjson")
    out.parent.mkdir(parents=True, exist_ok=True)
    with tmp.open("w", encoding="utf-8") as w:
        for x in results:
            w.write(json.dumps(x, ensure_ascii=False) + "\n")
    tmp.replace(out)
    report = {
        "input": str(src),
        "output": str(out),
        "repositories_processed": len(results),
        **counts,
        "workers": args.workers,
        "request_timeout_seconds": 10,
        "max_items": args.max_items,
        "note": "Parallel bounded enrichment; license values come only from source metadata or identifiable license files.",
    }
    Path("data/prospection/source_enrichment_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
