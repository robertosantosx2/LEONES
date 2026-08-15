#!/usr/bin/env python3
"""Conservatively ingest model discoveries into the Atlas feed."""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROS=ROOT/'data'/'prospection'
OUT=PROS/'atlas_feed.csv'
REVIEW=PROS/'atlas_review_queue.csv'
FIELDS=['source_file','source_id','model_id','model_name','organization','release_date','source_url','license','weights_url','code_url','runtime','format','quantization','hardware_id','workload','jgb_level','jgb_confidence','quality_score','tokens_per_second','estimated_memory_gb','context_tokens','evidence_status','notes']
FILES=['classified_discoveries.ndjson','additional_forge_discoveries.ndjson']
ALIASES={'id':'source_id','model':'model_id','name':'model_name','url':'source_url','evidence_url':'source_url','date':'release_date','license_name':'license','weights':'weights_url','code':'code_url'}

def flat(v):
    if isinstance(v,(str,int,float)): return str(v)
    if isinstance(v,list): return '; '.join(flat(x) for x in v)
    if isinstance(v,dict): return json.dumps(v,ensure_ascii=False,sort_keys=True)
    return ''

def is_model(obj):
    typ=str(obj.get('type','')).lower()
    cats=obj.get('categories',[])
    if isinstance(cats,str): cats=[cats]
    cats={str(x).lower() for x in cats}
    return typ in {'model','llm','language_model','foundation_model'} or 'models' in cats or 'llm' in cats

def normalize(obj, source):
    r={f:'' for f in FIELDS}; r['source_file']=source
    for k,v in obj.items():
        target=ALIASES.get(k.strip(),k.strip())
        if target in r: r[target]=flat(v).strip()
    if obj.get('evidence_url'): r['source_url']=flat(obj['evidence_url']).strip()
    if not r['model_name']: r['model_name']=r['model_id']
    if not r['model_id']: r['model_id']=r['model_name']
    if not r['source_id']: r['source_id']=r['source_url'] or r['model_id']
    status=(r['evidence_status'] or '').lower()
    if status not in {'verified','confirmed'}: r['evidence_status']='discovered'
    return r

def main():
    records=[]
    for name in FILES:
        p=PROS/name
        if not p.exists(): continue
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            try:
                obj=json.loads(line)
                if is_model(obj): records.append(normalize(obj,name))
            except json.JSONDecodeError: continue
    unique={}
    for r in records:
        key=r['source_id'] or f"{r['model_id']}|{r['source_url']}"
        if key: unique.setdefault(key,r)
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(unique.values())
    review=[r for r in unique.values() if r['evidence_status']!='verified']
    with REVIEW.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(review)
    print(f'Atlas ingest: {len(unique)} model records; {len(review)} require verification')
if __name__=='__main__': main()
