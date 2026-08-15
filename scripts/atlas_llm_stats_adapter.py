#!/usr/bin/env python3
"""Normalize LLM Stats benchmark observations into Atlas evidence."""
from __future__ import annotations
import csv,datetime as dt,hashlib,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
IN=ROOT/'data/prospection/llm_stats_observations.csv'
OUT=ROOT/'data/prospection/atlas_external_evidence.csv'
URL='https://llm-stats.com/benchmarks'
FIELDS=['model_id','model_name','source_type','source_url','retrieved_at','claim','metric','value','unit','benchmark','hardware','runtime','quantization','workload','evidence_status','source_record_id','extraction_method']
def main():
 if not IN.exists(): print(f'No structured LLM Stats input yet: {IN}'); return
 rows=[]; existing=[]
 if OUT.exists():
  with OUT.open(encoding='utf-8',newline='') as f: existing=list(csv.DictReader(f))
 seen={r.get('source_record_id') for r in existing}; now=dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
 with IN.open(encoding='utf-8',newline='') as f: rows=list(csv.DictReader(f))
 added=0
 for r in rows:
  model=r.get('model_name',''); benchmark=r.get('benchmark',''); metric=r.get('metric',''); value=r.get('value',''); unit=r.get('unit','')
  claim=f'{model}: {benchmark} {metric}={value} {unit}'.strip(); key='|'.join([model,benchmark,metric,value,r.get('setting','')]); rid='llm_stats:'+hashlib.sha256(key.encode()).hexdigest()[:16]
  if rid in seen: continue
  existing.append({'model_id':r.get('model_id',''),'model_name':model,'source_type':'llm_stats','source_url':r.get('source_url') or URL,'retrieved_at':r.get('retrieved_at') or now,'claim':claim,'metric':metric,'value':value,'unit':unit,'benchmark':benchmark,'hardware':r.get('hardware',''),'runtime':r.get('runtime',''),'quantization':r.get('quantization',''),'workload':r.get('workload','benchmark'),'evidence_status':'reported','source_record_id':rid,'extraction_method':'structured_input'}); seen.add(rid); added+=1
 OUT.parent.mkdir(parents=True,exist_ok=True)
 with OUT.open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction='ignore'); w.writeheader(); w.writerows(existing)
 print(f'LLM Stats: {added} new observations; {len(existing)} total evidence records')
if __name__=='__main__': main()
