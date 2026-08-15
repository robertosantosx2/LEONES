#!/usr/bin/env python3
"""Audit canonical model identity without silently merging records."""
from __future__ import annotations
import csv,re,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/'data/prospection/atlas_feed.csv'
OUT=ROOT/'data/prospection/atlas_identity_audit.csv'

def norm(v): return re.sub(r'[^a-z0-9]+',' ',(v or '').lower()).strip()
def repo_key(r):
    u=(r.get('repository_url') or r.get('source_url') or '').strip().rstrip('/')
    m=re.search(r'(?:github\.com|huggingface\.co)/([^/]+/[^/?#]+)',u,re.I)
    return norm(m.group(1)) if m else ''
def identity(r):
    mid=norm(r.get('model_id')); rk=repo_key(r); org=norm(r.get('organization')); name=norm(r.get('model_name'))
    return mid or rk or (org+' '+name).strip()
def main():
    with FEED.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    by=collections.defaultdict(list)
    for i,r in enumerate(rows,1): by[identity(r)].append((i,r))
    out=[]
    for key,items in by.items():
        if not key: continue
        if len(items)==1: status='unique'; risk='low'
        else:
            variants={norm(x[1].get('quantization')) for x in items}; hw={norm(x[1].get('hardware_id')) for x in items}; names={norm(x[1].get('model_name')) for x in items}
            if len(variants)>1 or len(hw)>1: status='same-model-multiple-artifacts-or-configs'; risk='review'
            elif len(names)>1: status='possible-collision'; risk='high'
            else: status='duplicate-candidate'; risk='high'
        for i,r in items: out.append({'identity_key':key,'row_number':i,'model_id':r.get('model_id',''),'model_name':r.get('model_name',''),'organization':r.get('organization',''),'repository_url':r.get('repository_url',''),'quantization':r.get('quantization',''),'hardware_id':r.get('hardware_id',''),'status':status,'risk':risk,'action':'retain' if risk=='low' else 'review-before-merge'})
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['identity_key','row_number','model_id','model_name','organization','repository_url','quantization','hardware_id','status','risk','action']);w.writeheader();w.writerows(out)
    c=collections.Counter(x['status'] for x in out); print(f'Identity audit: rows={len(rows)} keys={len(by)} unique={c["unique"]} duplicate_groups={sum(1 for v in by.values() if len(v)>1)} output={OUT}')
if __name__=='__main__': main()
