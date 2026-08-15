#!/usr/bin/env python3
"""Normalize LM Arena leaderboard exports into Atlas evidence.

The adapter accepts a structured CSV export because the public Arena UI is
interactive. It never guesses hidden endpoints or treats a displayed rank as
an independently verified capability score.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
IN = ROOT / "data/prospection/lm_arena_observations.csv"
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"
URL = "https://chat.lmsys.org/"
FIELDS=["model_id","model_name","source_type","source_url","retrieved_at","claim","metric","value","unit","benchmark","hardware","runtime","quantization","workload","evidence_status","source_record_id","extraction_method"]

ALIASES={"elo":"Elo", "elo_rating":"Elo", "rating":"rating", "rank":"rank", "win_rate":"win_rate"}

def main():
    if not IN.exists():
        print(f"No structured LM Arena input yet: {IN}")
        return
    existing=[]
    if OUT.exists():
        with OUT.open(encoding="utf-8",newline="") as f: existing=list(csv.DictReader(f))
    seen={r.get("source_record_id") for r in existing}
    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    with IN.open(encoding="utf-8",newline="") as f: src=list(csv.DictReader(f))
    added=0
    for r in src:
        metric=ALIASES.get((r.get("metric") or "").lower(), r.get("metric", ""))
        model=r.get("model_name",""); value=r.get("value",""); unit=r.get("unit","")
        claim=f"{model}: {metric}={value} {unit}".strip()
        key="|".join([model,metric,value,unit,r.get("arena_category","")])
        rid="lm_arena:"+hashlib.sha256(key.encode()).hexdigest()[:16]
        if rid in seen: continue
        existing.append({"model_id":r.get("model_id",""),"model_name":model,"source_type":"lm_arena","source_url":r.get("source_url") or URL,"retrieved_at":r.get("retrieved_at") or now,"claim":claim,"metric":metric,"value":value,"unit":unit,"benchmark":"LM Arena","hardware":"","runtime":"","quantization":"","workload":r.get("arena_category","chat"),"evidence_status":"reported","source_record_id":rid,"extraction_method":"structured_input"})
        seen.add(rid); added+=1
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore"); w.writeheader(); w.writerows(existing)
    print(f"LM Arena: {added} new observations; {len(existing)} total evidence records")

if __name__ == "__main__": main()
