#!/usr/bin/env python3
"""Build the external-evidence queue without promoting discoveries to Atlas.

The first evidence layer is designed around Hugging Face, LM Arena, Artificial
Analysis and official manufacturer sources. This script only classifies URLs
already discovered by LEONES; it never invents a source URL or a claim.
"""
from __future__ import annotations
import csv
from pathlib import Path
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'data'/'prospection'/'atlas_feed.csv'
OUT=ROOT/'data'/'prospection'/'atlas_external_evidence.csv'
FIELDS=['model_id','model_name','source_type','url','retrieved_at','claim','evidence_status']


def source_type(url):
    host=urlparse(url).netloc.lower().split(':')[0]
    if host.endswith('huggingface.co'): return 'hugging_face'
    if host.endswith('lmarena.ai') or host.endswith('arena.ai'): return 'lm_arena'
    if host.endswith('artificialanalysis.ai'): return 'artificial_analysis'
    return ''


def main():
    if not IN.exists():
        OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(','.join(FIELDS)+'\n',encoding='utf-8'); return
    rows=[]; seen=set()
    with IN.open(encoding='utf-8',newline='') as fh:
        for r in csv.DictReader(fh):
            urls=[r.get('source_url',''),r.get('weights_url',''),r.get('code_url','')]
            for url in urls:
                st=source_type(url or '')
                if not st: continue
                key=(r.get('model_id',''),st,url)
                if key in seen: continue
                seen.add(key)
                rows.append({'model_id':r.get('model_id',''),'model_name':r.get('model_name',''),
                             'source_type':st,'url':url,'retrieved_at':'','claim':'','evidence_status':'reported'})
    with OUT.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    print(f'External evidence queue: {len(rows)} records -> {OUT}')

if __name__=='__main__': main()
