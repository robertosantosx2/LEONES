#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,os,urllib.parse,urllib.request
from datetime import datetime,timezone
from pathlib import Path
UA='LEONES-Atlas-Prospection/1.0'; ROOT=Path(__file__).resolve().parents[2]
def request_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/json'})
    token=os.getenv('GITHUB_TOKEN')
    if token and 'api.github.com' in url:req.add_header('Authorization','Bearer '+token)
    with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read().decode()),r.status
def github(q,limit=30):
    u='https://api.github.com/search/repositories?'+urllib.parse.urlencode({'q':q,'sort':'updated','order':'desc','per_page':limit});d,s=request_json(u);now=datetime.now(timezone.utc).isoformat();rows=[]
    for x in d.get('items',[]):
        l=x.get('license') or {};rows.append({'type':'software','name':x.get('full_name',x.get('name','')),'url':x.get('html_url',''),'description':x.get('description',''),'source':'github','source_url':'https://github.com','evidence_url':x.get('html_url',''),'license':l.get('spdx_id',''),'license_status':'declared' if l.get('spdx_id') else 'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,s
def gitlab(q,limit=30):
    u='https://gitlab.com/api/v4/projects?'+urllib.parse.urlencode({'search':q,'order_by':'last_activity_at','sort':'desc','per_page':limit});d,s=request_json(u);now=datetime.now(timezone.utc).isoformat();rows=[]
    for x in d:
        rows.append({'type':'software','name':x.get('path_with_namespace',x.get('name','')),'url':x.get('web_url',''),'description':x.get('description',''),'source':'gitlab','source_url':'https://gitlab.com','evidence_url':x.get('web_url',''),'license':'','license_status':'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,s
def hf(q,limit=30):
    u='https://huggingface.co/api/models?'+urllib.parse.urlencode({'search':q,'limit':limit,'sort':'lastModified','direction':-1});d,s=request_json(u);now=datetime.now(timezone.utc).isoformat();rows=[]
    for x in d:
        ident=x.get('id','')
        if ident: rows.append({'type':'model','name':ident,'url':'https://huggingface.co/'+ident,'source':'huggingface','source_url':'https://huggingface.co','evidence_url':'https://huggingface.co/'+ident,'license':x.get('license',''),'license_status':'declared' if x.get('license') else 'unvalidated','observed_at':now,'query':q,'publication_status':'discovered'})
    return rows,s
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(ROOT/'data/prospection/live_discoveries.ndjson'));p.add_argument('--max-queries',type=int,default=12);a=p.parse_args();qs=[('github','LLM'),('github','LLM inference'),('github','agent framework'),('github','MCP server'),('gitlab','LLM'),('gitlab','agent framework'),('gitlab','inference runtime'),('huggingface','text-generation'),('huggingface','code-generation'),('huggingface','vision-language'),('huggingface','embedding'),('huggingface','reranker')][:a.max_queries];o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True);total=0
    with o.open('a',encoding='utf-8') as f:
        for source,q in qs:
            try:
                rows,status={'github':github,'gitlab':gitlab,'huggingface':hf}[source](q)
                for row in rows:f.write(json.dumps(row,ensure_ascii=False)+'\n')
                total+=len(rows);print(json.dumps({'source':source,'query':q,'status':status,'count':len(rows)},ensure_ascii=False))
            except Exception as e: print(json.dumps({'source':source,'query':q,'status':'error','error':str(e)},ensure_ascii=False))
    print(json.dumps({'total':total,'output':str(o)},ensure_ascii=False))
if __name__=='__main__':main()
