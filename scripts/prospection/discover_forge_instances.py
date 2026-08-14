#!/usr/bin/env python3
"""Discover concrete public Forgejo/Gitea instances from a seed list.

This is deliberately conservative: it only records instances whose public API
responds successfully. It does not crawl arbitrary hosts or publish projects.
"""
from __future__ import annotations
import argparse, json, urllib.request
from pathlib import Path

SEEDS = [
    "https://codeberg.org",
    "https://forgejo.org",
    "https://next.forgejo.org",
    "https://gitea.com",
]


def probe(base: str):
    base = base.rstrip("/")
    for path in ("/api/v1/version", "/api/v1/repos/search?q=LLM&limit=1"):
        try:
            req = urllib.request.Request(base + path, headers={"User-Agent": "LEONES-prospection/1.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                if r.status == 200:
                    return {"url": base, "api": base + "/api/v1", "status": "reachable", "probe": path}
        except Exception:
            pass
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="data/prospection/forge_instances.ndjson")
    args = ap.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    seen = set()
    for seed in SEEDS:
        row = probe(seed)
        if row and row["url"] not in seen:
            seen.add(row["url"])
            rows.append(row)
    out.write_text("\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + ("\n" if rows else ""), encoding="utf-8")
    print(json.dumps({"instances_discovered": len(rows), "output": str(out), "instances": rows}, ensure_ascii=False))

if __name__ == "__main__":
    main()
