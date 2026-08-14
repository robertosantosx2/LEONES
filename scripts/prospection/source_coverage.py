#!/usr/bin/env python3
"""Inventory every registered source and report its operational state.

This deliberately separates coverage from discovery and from the License Gate:
a source can be registered, probed, queried, unsupported, or errored without
being treated as a publication decision.
"""
from __future__ import annotations
import json, os, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "scripts/prospection/sources_registry.json"
OUT = ROOT / "data/prospection/source_coverage_report.json"
UA = "LEONES-Atlas-Prospection/2.4"


def probe(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=12) as r:
            return {"status": "reachable", "http_status": r.status, "final_url": r.geturl()}
    except urllib.error.HTTPError as e:
        return {"status": "http_error", "http_status": e.code, "final_url": getattr(e, "url", url)}
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "message": str(e)[:300]}


def main():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = []
    for source in registry.get("sources", []):
        row = {"id": source["id"], "name": source["name"], "url": source["url"], "kind": source.get("kind"), "priority": source.get("priority")}
        row.update(probe(source["url"]))
        if source["id"] in {"sourcehut", "srht"}:
            row["authentication_configured"] = bool(os.getenv("LEONES_SOURCEHUT_TOKEN"))
        elif source["id"] in {"gitlab", "gitlab-ce", "framagit"}:
            row["authentication_configured"] = bool(os.getenv("LEONES_GITLAB_TOKEN") or os.getenv("LEONES_FRAMAGIT_TOKEN"))
        elif source["id"] in {"huggingface", "huggingface-papers"}:
            row["authentication_configured"] = bool(os.getenv("HF_TOKEN"))
        else:
            row["authentication_configured"] = False
        rows.append(row)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "registered_sources": len(rows), "sources": rows, "note": "Coverage inventory only. It does not approve licenses or publish to Atlas."}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
