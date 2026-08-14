#!/usr/bin/env python3
"""Build the public LEONES prospection feed from the classified pipeline output.

The web feed is a publication view, not an approval mechanism. Records that have
not explicitly reached an approved/verified publication state remain pending.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

SRC = Path("data/prospection/classified_discoveries.ndjson")
OUT = Path("web/data/prospeccion.json")


def main() -> None:
    rows = []
    if SRC.exists():
        for line in SRC.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    x = json.loads(line)
                except json.JSONDecodeError:
                    continue
                # Never manufacture approval: only an explicit verified/publication
                # state is allowed to become verified in the public UI.
                state = str(x.get("publication_status") or x.get("status") or "").lower()
                verified = state in {"approved", "verified", "published"}
                rows.append({
                    "discovery_id": x.get("discovery_id"),
                    "name": x.get("name") or x.get("repository"),
                    "repository": x.get("repository") or x.get("name"),
                    "url": x.get("url"),
                    "description": x.get("description"),
                    "category": x.get("category") or x.get("type"),
                    "type": x.get("type"),
                    "license": x.get("license") or x.get("license_spdx"),
                    "open_weight": bool(x.get("open_weight")),
                    "source": x.get("source"),
                    "updated": x.get("updated") or x.get("discovered_at"),
                    "stars": x.get("stars"),
                    "status": "verified" if verified else "pending",
                    "publication_status": x.get("publication_status"),
                    "license_gate": x.get("license_gate"),
                    "provenance": x.get("provenance") or x.get("provenance_records"),
                })
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SRC),
        "publication_is_not_approval": True,
        "items": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"published_items": len(rows), "output": str(OUT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
