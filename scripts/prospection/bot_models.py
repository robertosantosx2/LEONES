#!/usr/bin/env python3
"""Model discovery bot.

Collects model records from explicit JSON/NDJSON feeds supplied by the daily
prospection job. It does not claim verification and never publishes directly.
Network fetching is intentionally kept outside this normalizer so source
adapters can be audited independently.
"""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

FIELDS=("name","family","organization","url","source","release_date","license","weights_url","architecture","parameters_total","parameters_active","capabilities")

def norm(v): return " ".join(str(v or "").strip().split())
def discovery_id(x):
    raw="|".join(norm(x.get(k)) for k in ("name","organization","url"))
    return hashlib.sha256(raw.lower().encode()).hexdigest()[:16]

def main():
    ap=argparse.ArgumentParser(description="Normalize model discoveries for LEONES Atlas")
    ap.add_argument("--input",default="data/prospection/model_sources.ndjson")
    ap.add_argument("--output",default="data/prospection/discoveries.ndjson")
    args=ap.parse_args(); src=Path(args.input); out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    rows=[]; seen=set(); now=datetime.now(timezone.utc).isoformat()
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            if not line.strip(): continue
            raw=json.loads(line); x={k:(norm(raw.get(k)) if k in FIELDS else raw[k]) for k in raw if k in FIELDS}
            if not x.get("name"): continue
            x.update({"type":"model","discovery_id":raw.get("discovery_id") or discovery_id(x),"discovered_at":raw.get("discovered_at") or now,"publication_status":"discovered","source":x.get("source") or x.get("url")})
            if x["discovery_id"] not in seen: seen.add(x["discovery_id"]); rows.append(x)
    out.write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows)+("\n" if rows else ""),encoding="utf-8")
    print(json.dumps({"bot":"models","discovered":len(rows),"output":str(out)},ensure_ascii=False))

if __name__=="__main__": main()
