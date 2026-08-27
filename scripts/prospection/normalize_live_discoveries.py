#!/usr/bin/env python3
"""Normaliza los descubrimientos de prospección en un NDJSON deduplicado."""

import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data/prospection/live_discoveries.ndjson"
OUT = ROOT / "data/prospection/discoveries.ndjson"


def key(x):
    return hashlib.sha256(
        "|".join(str(x.get(k, "")) for k in ("source", "url", "name")).encode()
    ).hexdigest()


def main():
    seen = set()
    rows = []
    if SRC.exists():
        for line in SRC.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                x = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = key(x)
            if k in seen:
                continue
            seen.add(k)
            x["discovery_id"] = k
            x.setdefault("license_status", "unvalidated")
            x.setdefault("publication_status", "discovered")
            rows.append(x)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "".join(json.dumps(x, ensure_ascii=False) + "\n" for x in rows),
        encoding="utf-8",
    )
    print(
        json.dumps({"input": len(rows), "output": str(OUT), "deduplicated": len(rows)})
    )


if __name__ == "__main__":
    main()
