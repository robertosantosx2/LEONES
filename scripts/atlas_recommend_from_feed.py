#!/usr/bin/env python3
"""Generate Atlas recommendations enriched with the clean hardware market price.

Price data comes only from data/hardware/hardware_prices.csv, which is produced
by the monthly hardware-price bot after its quality-control stage. Missing
prices remain unknown and never become estimates.
"""
from __future__ import annotations
import argparse, csv, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "data/prospection/atlas_feed.csv"
PRICES = ROOT / "data/hardware/hardware_prices.csv"
OUT = ROOT / "data/prospection/atlas_recommendations.csv"
FIELDS = ["rank","model_id","model_name","variant","quantization","runtime","hardware_id","workload","estimated_memory_gb","context_tokens","tokens_per_second","quality_score","jgb_level","jgb_confidence","fit_score","confidence","price_eur","price_source","price_observed_at","price_quality","value_score","reason"]

def num(v):
    try: return float(v) if v not in (None, "") else None
    except (ValueError, TypeError): return None

def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def price_key(name):
    n=norm(name)
    # Keep distinctive component identifiers; remove generic retail wording.
    n=re.sub(r"\b(geforce|nvidia|intel|amd|processor|procesador|cpu|gpu|tarjeta|grafica|gr[aá]fica|memory|memoria|ram|desktop|box|retail|tray)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()

def load_prices():
    if not PRICES.exists(): return []
    with PRICES.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def match_price(model_name, prices):
    target=price_key(model_name)
    if not target: return None
    best=None; best_score=0
    for p in prices:
        candidate=price_key(p.get("model", ""))
        if not candidate: continue
        a=set(target.split()); b=set(candidate.split())
        common=len(a & b)
        if not common: continue
        score=common/max(len(a),len(b))
        if candidate in target or target in candidate: score += .45
        # Exact family/model tokens should dominate capacity-only matches.
        if score > best_score:
            best_score=score; best=p
    return best if best_score >= .55 else None

def recommend(rows, prices, workload, hardware, ram, vram, context, min_jgb=None, prefer_jgb=False):
    limit = ram + vram; out=[]
    for r in rows:
        if not r.get("model_id") and not r.get("model_name"): continue
        if r.get("workload") and r["workload"] != workload: continue
        if r.get("hardware_id") and r["hardware_id"] != hardware: continue
        mem=num(r.get("estimated_memory_gb")); ctx=num(r.get("context_tokens")); runtime=(r.get("runtime") or "").strip(); quant=(r.get("quantization") or "").strip()
        if mem is None or ctx is None or not runtime or not quant: continue
        if mem > limit or ctx < context: continue
        jgb=num(r.get("jgb_level")); tps=num(r.get("tokens_per_second")); quality=num(r.get("quality_score"))
        if min_jgb is not None and (jgb is None or jgb < min_jgb): continue
        q=(quality/100) if quality is not None else 0; s=min((tps or 0)/50,1); m=max(0,1-mem/max(limit,1)); o=(jgb/5) if jgb is not None else 0
        score=.35*q+.25*s+.15*m+.15+(.10*o if prefer_jgb else 0)
        p=match_price(r.get("model_name") or r.get("model_id"), prices)
        price=num(p.get("price_eur")) if p else None
        # Value score is deliberately separate from technical fit: price never
        # overrides hardware/model viability or the JGB filter.
        value_score=None
        if price is not None and score > 0:
            value_score=score/(price/100.0)
        evidence_count=sum(x is not None for x in (mem,ctx,tps,quality,jgb)); confidence="high" if evidence_count == 5 else "medium" if evidence_count >= 3 else "low"
        reason=["technical viability supported by deployment evidence","quality evidence="+("available" if quality is not None else "unknown"),"performance evidence="+("available" if tps is not None else "unknown"),"JGB="+(str(int(jgb)) if jgb is not None else "unknown"),"price="+(f"{price:.2f} EUR from {p.get('source')}" if p else "unknown")]
        out.append((score,r,conf,"; ".join(reason),p,value_score))
    out.sort(key=lambda x:x[0], reverse=True); return out

def main():
    p=argparse.ArgumentParser(); p.add_argument("--workload",required=True); p.add_argument("--hardware",required=True); p.add_argument("--ram",type=float,required=True); p.add_argument("--vram",type=float,default=0); p.add_argument("--context",type=int,default=4096); p.add_argument("--min-jgb",type=int); p.add_argument("--prefer-jgb",action="store_true"); p.add_argument("--out",default=str(OUT)); a=p.parse_args()
    with FEED.open(encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
    prices=load_prices()
    ranked=recommend(rows,prices,a.workload,a.hardware,a.ram,a.vram,a.context,a.min_jgb,a.prefer_jgb)
    with open(a.out,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader()
        for i,(score,r,conf,reason,p,value_score) in enumerate(ranked,1):
            w.writerow({"rank":i,**{k:r.get(k,"") for k in FIELDS if k in r},"fit_score":f"{score:.4f}","confidence":conf,"price_eur":p.get("price_eur","") if p else "","price_source":p.get("source","") if p else "","price_observed_at":p.get("observed_at","") if p else "","price_quality":"accepted" if p else "unknown","value_score":f"{value_score:.6f}" if value_score is not None else "","reason":reason})
    print(f"{len(ranked)} recommendations -> {a.out}; price observations available={len(prices)}")
if __name__ == "__main__": main()
