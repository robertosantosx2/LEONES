#!/usr/bin/env python3
"""Generate contextual Atlas recommendations from the normalized prospection feed.

Only evidence already present in atlas_feed.csv is used. Missing metrics remain
unknown; the script never fabricates performance, quality or JGB values.
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
OUT = ROOT / "data/prospection/atlas_recommendations.csv"

FIELDS = ["rank","model_id","model_name","variant","quantization","runtime","hardware_id","workload","estimated_memory_gb","context_tokens","tokens_per_second","quality_score","jgb_level","jgb_confidence","fit_score","confidence","reason"]

def num(v):
    try: return float(v) if v not in (None, "") else None
    except ValueError: return None

def recommend(rows, workload, hardware, ram, vram, context, min_jgb=None, prefer_jgb=False):
    limit = ram + vram
    out=[]
    for r in rows:
        if r.get("workload") and r["workload"] != workload: continue
        if r.get("hardware_id") and r["hardware_id"] != hardware: continue
        mem=num(r.get("estimated_memory_gb")); ctx=num(r.get("context_tokens"))
        jgb=num(r.get("jgb_level")); tps=num(r.get("tokens_per_second")); quality=num(r.get("quality_score"))
        reasons=[]
        if mem is not None and mem > limit: continue
        if ctx is not None and ctx < context: continue
        if min_jgb is not None and (jgb is None or jgb < min_jgb): continue
        q=(quality/100) if quality is not None else 0
        s=min((tps or 0)/50,1)
        m=max(0,1-(mem or limit)/max(limit,1))
        o=(jgb/5) if jgb is not None else 0
        score=.35*q+.25*s+.15*m+.15+(.10*o if prefer_jgb else 0)
        reasons.append("viable under supplied hardware/workload constraints")
        reasons.append("quality evidence=" + ("available" if quality is not None else "unknown"))
        reasons.append("performance evidence=" + ("available" if tps is not None else "unknown"))
        reasons.append("JGB=" + (str(int(jgb)) if jgb is not None else "unknown"))
        confidence="high" if all(x is not None for x in (mem,ctx,tps,quality,jgb)) else "low"
        out.append((score,r,confidence,"; ".join(reasons)))
    out.sort(key=lambda x:x[0], reverse=True)
    return out

def main():
    p=argparse.ArgumentParser(); p.add_argument("--workload",required=True); p.add_argument("--hardware",required=True); p.add_argument("--ram",type=float,required=True); p.add_argument("--vram",type=float,default=0); p.add_argument("--context",type=int,default=4096); p.add_argument("--min-jgb",type=int); p.add_argument("--prefer-jgb",action="store_true"); p.add_argument("--out",default=str(OUT)); a=p.parse_args()
    with FEED.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    ranked=recommend(rows,a.workload,a.hardware,a.ram,a.vram,a.context,a.min_jgb,a.prefer_jgb)
    fields=FIELDS
    with open(a.out,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
        for i,(score,r,conf,reason) in enumerate(ranked,1):
            w.writerow({"rank":i,**{k:r.get(k,"") for k in fields if k in r},"fit_score":f"{score:.4f}","confidence":conf,"reason":reason})
    print(f"{len(ranked)} recommendations -> {a.out}")
if __name__ == "__main__": main()
