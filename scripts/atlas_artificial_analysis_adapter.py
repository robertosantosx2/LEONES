#!/usr/bin/env python3
"""Normalize Artificial Analysis observations into Atlas evidence.

This adapter intentionally does not guess undocumented endpoints or scrape
interactive charts. It accepts structured observations supplied through a
CSV export/API response and preserves their conditions and provenance.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
IN = ROOT / "data/prospection/artificial_analysis_observations.csv"
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"
URL = "https://artificialanalysis.ai/"
FIELDS = ["model_id","model_name","source_type","source_url","retrieved_at","claim","metric","value","unit","benchmark","hardware","runtime","quantization","workload","evidence_status","source_record_id","extraction_method"]

METRIC_ALIASES = {"ttft":"TTFT", "time_to_first_token":"TTFT", "tokens_per_second":"throughput", "tok/s":"throughput", "cost_per_million_tokens":"cost_per_1m_tokens", "price":"cost_per_1m_tokens"}

def main():
    if not IN.exists():
        print(f"No structured Artificial Analysis input yet: {IN}")
        return
    existing=[]
    if OUT.exists():
        with OUT.open(encoding="utf-8",newline="") as f: existing=list(csv.DictReader(f))
    seen={r.get("source_record_id") for r in existing}
    now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    with IN.open(encoding="utf-8",newline="") as f: src=list(csv.DictReader(f))
    added=0
    for r in src:
        metric=METRIC_ALIASES.get((r.get("metric") or "").lower(), r.get("metric", ""))
        model=r.get("model_name", "")
        value=r.get("value", "")
        unit=r.get("unit", "")
        claim=f"{model}: {metric}={value} {unit}".strip()
        key="|".join([model,metric,value,unit,r.get("hardware",""),r.get("runtime","")])
        rid="aa:"+hashlib.sha256(key.encode()).hexdigest()[:16]
        if rid in seen: continue
        existing.append({"model_id":r.get("model_id",""),"model_name":model,"source_type":"artificial_analysis","source_url":r.get("source_url") or URL,"retrieved_at":r.get("retrieved_at") or now,"claim":claim,"metric":metric,"value":value,"unit":unit,"benchmark":r.get("benchmark",""),"hardware":r.get("hardware",""),"runtime":r.get("runtime",""),"quantization":r.get("quantization",""),"workload":r.get("workload",""),"evidence_status":"reported","source_record_id":rid,"extraction_method":"structured_input"})
        seen.add(rid); added+=1
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore"); w.writeheader(); w.writerows(existing)
    print(f"Artificial Analysis: {added} new structured observations; {len(existing)} total evidence records")

if __name__ == "__main__": main()
