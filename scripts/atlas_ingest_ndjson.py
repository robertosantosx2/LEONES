#!/usr/bin/env python3
"""Ingest LEONES prospection NDJSON into the normalized Atlas feed.

Discovery is never promoted to verified evidence automatically. The adapter
maps common fields, preserves the original status, deduplicates records and
writes a review queue for anything requiring verification.
"""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROS=ROOT/'data'/'prospection'
OUT=PROS/'atlas_feed.csv'
REVIEW=PROS/'atlas_review_queue.csv'
FIELDS=['source_file','source_id','model_id','model_name','organization','release_date','source_url','license','weights_url','code_url','runtime','format','quantization','hardware_id','workload','jgb_level','jgb_confidence','quality_score','tokens_per_second','estimated_memory_gb','context_tokens','evidence_status','notes']
FILES=['classified_discoveries.ndjson','atlas_candidates.ndjson','additional_forge_discoveries.ndjson','atlas_review_queue.ndjson']
ALIASES={'id':'source_id','model':'model_id','name':'model_name','url':'source_url','date':'release_date','license_name':'license','weights':'weights_url','code':'code_url'}

def flat(v):
    if isinstance(v,(str,int,float)): return str(v)
    if isinstance(v,list): return '; '.join(flat(x) for x in v)
    if isinstance(v,dict): return json.dumps(v,ensure_ascii=False,sort_keys=True)
    return ''

def normalize(obj, source):
    r={f:'' for f in FIELDS}; r['source_file']=source
    for k,v in obj.items():
        k=ALIASES.get(k.strip(),k.strip())
        if k in r: r[k]=flat(v).strip()
    if not r['source_id']:
        r['source_id']=r['source_url'] or r['model_id']
    status=(r['evidence_status'] or '').lower()
    # Conservative promotion: only explicit verified evidence may be verified.
    if status not in {'verified','confirmed'}: r['evidence_status']='discovered'
    return r

def main():
    records=[]
    for name in FILES:
        p=PROS/name
        if not p.exists(): continue
        for line in p.read_text(encoding='utf-8').splitlines():
            if not line.strip(): continue
            try: records.append(normalize(json.loads(line),name))
            except json.JSONDecodeError: continue
    unique={}
    for r in records:
        key=r['source_id'] or f"{r['model_id']}|{r['source_url']}"
        if key and key not in unique: unique[key]=r
    OUT.parent.mkdir(parents=True,exist_ok=True)
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(unique.values())
    review=[r for r in unique.values() if r['evidence_status']!='verified']
    with REVIEW.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(review)
    print(f'Atlas ingest: {len(unique)} records; {len(review)} require verification')
if __name__=='__main__': main()
