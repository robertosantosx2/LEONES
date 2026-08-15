#!/usr/bin/env python3
"""Generate deterministic quality flags for the Atlas discovery feed.

Flags are warnings/review work, not truth values. The script never upgrades
verification state and never invents missing metadata.
"""
from __future__ import annotations
import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
IN=ROOT/'data/prospection/atlas_feed.csv'
OUT=ROOT/'data/prospection/atlas_quality_flags.csv'
FIELDS=['entity_type','entity_id','flag_type','severity','field_name','message','detected_at','resolved_at','resolution']
REQUIRED=['model_id','model_name','source_url']


def main():
    flags=[]; now=datetime.now(timezone.utc).isoformat()
    if not IN.exists():
        OUT.parent.mkdir(parents=True,exist_ok=True)
        with OUT.open('w',encoding='utf-8',newline='') as fh: csv.DictWriter(fh,fieldnames=FIELDS).writeheader()
        return
    with IN.open(encoding='utf-8',newline='') as fh: rows=list(csv.DictReader(fh))
    seen={}
    for r in rows:
        eid=r.get('model_id','') or r.get('source_id','') or r.get('model_name','')
        for f in REQUIRED:
            if not r.get(f,'').strip():
                flags.append({'entity_type':'model','entity_id':eid,'flag_type':'missing','severity':'high' if f in {'model_id','model_name'} else 'medium','field_name':f,'message':f'Missing required discovery field: {f}','detected_at':now,'resolved_at':'','resolution':''})
        if r.get('evidence_status','').lower() not in {'verified'}:
            flags.append({'entity_type':'model','entity_id':eid,'flag_type':'unverified','severity':'medium','field_name':'evidence_status','message':'Discovery is not verified; keep outside official verified aggregates.','detected_at':now,'resolved_at':'','resolution':''})
        key=(r.get('model_name','').strip().lower(),r.get('organization','').strip().lower())
        if key != ('',''):
            seen.setdefault(key,[]).append(eid)
    for key, ids in seen.items():
        if len(set(ids))>1:
            for eid in set(ids):
                flags.append({'entity_type':'model','entity_id':eid,'flag_type':'identity_collision','severity':'medium','field_name':'model_name','message':f'Possible identity collision for {key[0]} / {key[1]}','detected_at':now,'resolved_at':'','resolution':''})
    with OUT.open('w',encoding='utf-8',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=FIELDS); w.writeheader(); w.writerows(flags)
    print(f'Atlas quality audit: {len(flags)} flags -> {OUT}')

if __name__=='__main__': main()
