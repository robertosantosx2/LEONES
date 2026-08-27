#!/usr/bin/env python3
"""Write adapter output as auditable NDJSON without publication."""

from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Dict, Any


def write(records: Iterable[Dict[str, Any]], path: str) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    count = 0
    with target.open("a", encoding="utf-8") as f:
        for x in records:
            if not x.get("name") or not x.get("url") or not x.get("source"):
                continue
            did = (
                x.get("discovery_id")
                or hashlib.sha256(
                    "|".join(str(x.get(k, "")) for k in ("type", "name", "url"))
                    .lower()
                    .encode()
                ).hexdigest()[:16]
            )
            if did in seen:
                continue
            y = dict(x)
            y["discovery_id"] = did
            y["discovered_at"] = (
                y.get("discovered_at") or datetime.now(timezone.utc).isoformat()
            )
            y["publication_status"] = "discovered"
            f.write(json.dumps(y, ensure_ascii=False) + "\n")
            seen.add(did)
            count += 1
    return count
