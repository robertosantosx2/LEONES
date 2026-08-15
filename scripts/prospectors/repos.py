#!/usr/bin/env python3
import json,sys,urllib.parse,urllib.request,urllib.error,os
from datetime import datetime,timezone

kind=sys.argv[1]
queries={'runtimes':'local LLM inference runtime','agents':'LLM agent framework local AI','skills':'LLM agent skills','harnesses':'LLM evaluation harness benchmark'}
q=urllib.parse.quote(queries[kind])
url='https://api.github.com/search/repositories?q='+q+'&sort=updated&order=desc&per_page=50'
req=urllib.request.Request(url,headers={'User-Agent':'LEONES-Atlas-Prospector/1.0','Accept':'application/vnd.github+json'})

items=[]
error=''
try:
    with urllib.request.urlopen(req,timeout=30) as response:
        data=json.load(response)
    items=data.get('items',[])
except urllib.error.HTTPError as exc:
    error=f'HTTP {exc.code}: {exc.reason}'
except (urllib.error.URLError, TimeoutError) as exc:
    error=f'network error: {exc}'

os.makedirs('data/discovery',exist_ok=True)
out={'generated_at':datetime.now(timezone.utc).isoformat(),'kind':kind,'policy':'discover-only; verify OSI license before recommendation','items':[],'error':error or None}
for x in items:
    lic=(x.get('license') or {}).get('spdx_id') or ''
    out['items'].append({'name':x.get('full_name'),'url':x.get('html_url'),'description':x.get('description'),'updated_at':x.get('updated_at'),'license':lic,'osi_status':'unknown','status':'external-unvalidated'})
with open('data/discovery/'+kind+'.json','w',encoding='utf-8') as f:
    json.dump(out,f,ensure_ascii=False,indent=2)

if error:
    print(f'WARNING: GitHub discovery unavailable for {kind}: {error}; wrote empty/partial discovery output and continued.')
else:
    print(f'GitHub discovery {kind}: {len(items)} repositories')
