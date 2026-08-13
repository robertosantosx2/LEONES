#!/usr/bin/env python3
"""Run registry-driven discovery against queryable forge instances.

Unknown or software-only routes are recorded as skipped rather than treated as
searchable repositories. Results remain candidates until normalization,
classification and the License Gate.
"""
from __future__ import annotations
import argparse,json,os,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
UA='LEONES-Atlas-Prospection/1.0'
QUERIES=['LLM','inference','agent','MCP','model','AI']

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    token=os.getenv('GITHUB_TOKEN')
    if token and 'gitlab' in url:req.add_header('Authorization','Bearer '+token)
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode()),r.status

def search_gitlab(base,q):
    u=base.rstrip('/')+'/api/v4/projects?'+urllib.parse.urlencode({'search':q,'order_by':'last_activity_at','sort':'desc','per_page':20})
    data,status=get(u); now=datetime.now(timezone.utc).isoformat(); rows=[]
    for x in data:
        rows.append({'type':'software','name':x.get('path_with_namespace',x.get('name','')),'url':x.get('web_url',''),'description':x.get('description') or '','source':'gitlab','source_url':base,'evidence_url':x.get('web_url',''),'license':'','license_status':'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,status

def search_forgejo(base,q):
    u=base.rstrip('/')+'/api/v1/repos/search?'+urllib.parse.urlencode({'q':q,'limit':20})
    data,status=get(u); now=datetime.now(timezone.utc).isoformat(); rows=[]
    for x in data.get('data',[]):
        url=x.get('html_url') or ''
        rows.append({'type':'software','name':x.get('full_name') or x.get('name',''),'url':url,'description':x.get('description') or '','source':'forgejo','source_url':base,'evidence_url':url,'license':'','license_status':'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,status

def search_pagure(base,q):
    u=base.rstrip('/')+'/api/0/projects?'+urllib.parse.urlencode({'pattern':q})
    data,status=get(u); now=datetime.now(timezone.utc).isoformat(); rows=[]
    items=data if isinstance(data,list) else data.get('projects',[])
    for x in items[:20]:
        url=x.get('url') or (base.rstrip('/')+'/'+x.get('fullname',''))
        rows.append({'type':'software','name':x.get('fullname') or x.get('name',''),'url':url,'description':x.get('description') or '','source':'pagure','source_url':base,'evidence_url':url,'license':'','license_status':'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,status

def main():
    p=argparse.ArgumentParser();p.add_argument('--targets',default='data/prospection/adapter_targets.ndjson');p.add_argument('--output',default='data/prospection/live_discoveries.ndjson');p.add_argument('--max-targets',type=int,default=50);p.add_argument('--queries',type=int,default=2);a=p.parse_args()
    targets=Path(a.targets); rows=[]; skipped=[]
    if targets.exists():
        for line in targets.read_text(encoding='utf-8').splitlines():
            if line.strip(): rows.append(json.loads(line))
    out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);total=0
    with out.open('a',encoding='utf-8') as f:
        for t in rows[:a.max_targets]:
            route=t.get('route'); base=t.get('source_url','')
            fn={'gitlab':search_gitlab,'forgejo':search_forgejo,'pagure':search_pagure}.get(route)
            if not fn:
                skipped.append({'source_id':t.get('source_id'),'route':route,'reason':'no executable adapter yet'});continue
            for q in QUERIES[:a.queries]:
                try:
                    found,status=fn(base,q)
                    for x in found:f.write(json.dumps(x,ensure_ascii=False)+'\n')
                    total+=len(found);print(json.dumps({'source':t.get('source_id'),'route':route,'query':q,'status':status,'count':len(found)},ensure_ascii=False))
                except Exception as e: print(json.dumps({'source':t.get('source_id'),'route':route,'query':q,'status':'error','error':str(e)},ensure_ascii=False))
    print(json.dumps({'targets':len(rows),'processed':min(len(rows),a.max_targets),'discovered':total,'skipped':skipped},ensure_ascii=False))

if __name__=='__main__':main()
