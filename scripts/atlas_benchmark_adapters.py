#!/usr/bin/env python3
"""Normalize structured coding/agent benchmark observations for Atlas.

Inputs are explicit CSV exports. No benchmark score is inferred from a web
page; provenance, split and evaluation conditions are preserved.
"""
from __future__ import annotations
import csv, datetime as dt, hashlib, pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'data/prospection/atlas_external_evidence.csv'
SOURCES={
 'swe_bench':('https://www.swebench.com/','data/prospection/swe_bench_observations.csv'),
 'livecodebench':('https://livecodebench.github.io/','data/prospection/livecodebench_observations.csv'),
}
FIELDS=['model_id','model_name','source_type','source_url','retrieved_at','claim','metric','value','unit','benchmark','hardware','runtime','quantization','workload','evidence_status','source_record_id','extraction_method']
def main():
 existing=[]
 if OUT.exists():
  with OUT.open(encoding='utf-8',newline='') as f: existing=list(csv.DictReader(f))
 seen={r.get('source_record_id') for r in existing}; added=0
 now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
 for source,(url,fn) in SOURCES.items():
  p=ROOT/fn
  if not p.exists(): print(f'No structured {source} input yet: {p}'); continue
  with p.open(encoding='utf-8',newline='') as f: rows=csv.DictReader(f)
  for r in rows:
   model=r.get('model_name',''); benchmark=r.get('benchmark') or source; metric=r.get('metric',''); value=r.get('value',''); unit=r.get('unit','')
   claim=f'{model}: {benchmark} {metric}={value} {unit}'.strip()
   key='|'.join([source,model,benchmark,metric,value,r.get('split',''),r.get('setting','')])
   rid=source+':'+hashlib.sha256(key.encode()).hexdigest()[:16]
   if rid in seen: continue
   existing.append({'model_id':r.get('model_id',''),'model_name':model,'source_type':source,'source_url':r.get('source_url') or url,'retrieved_at':r.get('retrieved_at') or now,'claim':claim,'metric':metric,'value':value,'unit':unit,'benchmark':benchmark,'hardware':r.get('hardware',''),'runtime':r.get('runtime',''),'quantization':r.get('quantization',''),'workload':r.get('workload','coding/agent'),'evidence_status':'reported','source_record_id':rid,'extraction_method':'structured_input'})
   seen.add(rid); added+=1
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with OUT.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore'); w.writeheader(); w.writerows(existing)
 print(f'Coding benchmarks: {added} new observations; {len(existing)} total evidence records')
if __name__=='__main__': main()
