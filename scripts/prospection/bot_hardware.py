#!/usr/bin/env python3
"""Normalize hardware/platform discoveries into the LEONES contract."""

from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

FIELDS = (
    "name",
    "organization",
    "url",
    "source",
    "release_date",
    "cpu",
    "gpu",
    "ram",
    "vram",
    "npu",
    "platform",
    "notes",
)


def norm(v):
    return " ".join(str(v or "").strip().split())


def did(x):
    return hashlib.sha256(
        "|".join(norm(x.get(k)) for k in ("name", "organization", "url"))
        .lower()
        .encode()
    ).hexdigest()[:16]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/prospection/hardware_sources.ndjson")
    ap.add_argument("--output", default="data/prospection/discoveries.ndjson")
    a = ap.parse_args()
    src = Path(a.input)
    out = Path(a.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    rows = []
    now = datetime.now(timezone.utc).isoformat()
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            x = {k: norm(r.get(k)) for k in FIELDS if k in r}
            if not x.get("name"):
                continue
            x.update(
                type="hardware",
                discovery_id=r.get("discovery_id") or did(x),
                discovered_at=r.get("discovered_at") or now,
                publication_status="discovered",
                source=x.get("source") or x.get("url"),
            )
            if x["discovery_id"] not in seen:
                seen.add(x["discovery_id"])
                rows.append(x)
    with out.open("a", encoding="utf-8") as f:
        for x in rows:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {"bot": "hardware", "discovered": len(rows), "output": str(out)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
