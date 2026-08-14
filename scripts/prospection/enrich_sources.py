#!/usr/bin/env python3
"""Source-specific enrichment for non-GitHub discoveries.

Collects repository metadata and license evidence from public GitLab and
Forgejo/Gitea APIs. Unknown licenses remain unknown; no license is inferred
from README prose.
"""
from __future__ import annotations
import argparse, base64, json, os, urllib.parse, urllib.request, urllib.error
from pathlib import Path

UA="LEONES-Atlas-Prospection/2.4"
LICENSE_FILES=("LICENSE","LICENSE.md","LICENSE.txt","COPYING","COPYING.md")

def get(url, token=None):
    h={"User-Agent":UA,"Accept":"application/json"}
    if token: h["Authorization"]=f"Bearer {token}"
    req=urllib.request.Request(url,headers=h)
    try:
        with urllib.request.urlopen(req,timeout=25) as r:
            return json.loads(r.read().decode("utf-8")),r.status,None
    except urllib.error.HTTPError as e:
        return None,e.code,e.reason
    except Exception as e:
        return None,None,str(e)

def raw(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    try:
        with urllib.request.urlopen(req,timeout=25) as r:return r.read().decode("utf-8",errors="replace")
    except Exception:return ""

def license_from_text(text):
    t=text.lower()
    patterns=[
      ("Apache-2.0",("apache license, version 2.0","licensed under the apache license, version 2.0")),
      ("MIT",("permission is hereby granted, free of charge",)),
      ("GPL-3.0",("gnu general public license version 3","gnu general public license, version 3")),
      ("GPL-2.0",("gnu general public license version 2","gnu general public license, version 2")),
      ("AGPL-3.0",("gnu affero general public license",)),
      ("LGPL-3.0",("gnu lesser general public license version 3",)),
      ("LGPL-2.1",("gnu lesser general public license version 2.1",)),
      ("MPL-2.0",("mozilla public license, version 2.0",)),
      ("BSD-3-Clause",("redistribution and use in source and binary forms", "neither the name of the")),
      ("ISC",("permission to use, copy, modify, and/or distribute this software",)),
    ]
    for spdx, needles in patterns:
        if any(n in t for n in needles): return spdx
    return ""

def enrich_gitlab(item, base, token=None):
    url=item.get("url","").rstrip("/")
    parsed=urllib.parse.urlparse(url); project=parsed.path.strip("/")
    if not project:return item
    api=f"{base.rstrip('/')}/api/v4/projects/{urllib.parse.quote(project,safe='')}"
    repo,status,err=get(api,token)
    if status!=200 or not repo:
        item["enrichment"]={"status":"error","http_status":status,"message":str(err)};return item
    lic=(repo.get("license") or {}).get("key") or (repo.get("license") or {}).get("name") or ""
    if lic:
        item["license"]=lic;item["license_status"]="declared_from_gitlab"
    item["description"]=repo.get("description") or item.get("description")
    item["enrichment"]={"status":"ok","platform":"gitlab","project_id":repo.get("id"),"default_branch":repo.get("default_branch"),"last_activity_at":repo.get("last_activity_at"),"license":lic,"license_url":(repo.get("license") or {}).get("url"),"web_url":repo.get("web_url")}
    if not lic:
        branch=repo.get("default_branch") or "main"
        for name in LICENSE_FILES:
            enc=urllib.parse.quote(name,safe="")
            data,st,_=get(f"{base.rstrip('/')}/api/v4/projects/{repo['id']}/repository/files/{enc}?ref={urllib.parse.quote(branch)}",token)
            if st==200 and data and data.get("content"):
                try:text=base64.b64decode(data["content"]).decode("utf-8",errors="replace")
                except Exception:text=""
                found=license_from_text(text)
                if found:
                    item["license"]=found;item["license_status"]="evidence_from_gitlab_license_file";item["enrichment"]["license_file"]=name;break
    return item

def enrich_forgejo(item, base):
    p=urllib.parse.urlparse(item.get("url","")).path.strip("/").split("/")
    if len(p)<2:return item
    owner,repo=p[0],p[1]
    api=f"{base.rstrip('/')}/api/v1/repos/{urllib.parse.quote(owner)}/{urllib.parse.quote(repo)}"
    data,status,err=get(api)
    if status!=200 or not data:
        item["enrichment"]={"status":"error","http_status":status,"message":str(err)};return item
    lic=(data.get("license") or {}).get("spdx_id") or (data.get("license") or {}).get("name") or data.get("license") or ""
    if lic:
        item["license"]=lic;item["license_status"]="declared_from_forgejo"
    item["description"]=data.get("description") or item.get("description")
    item["enrichment"]={"status":"ok","platform":"forgejo-gitea","repository_id":data.get("id"),"default_branch":data.get("default_branch"),"updated_at":data.get("updated_at"),"license":lic,"html_url":data.get("html_url")}
    if not lic:
        branch=data.get("default_branch") or "main"
        for name in LICENSE_FILES:
            raw_url=f"{base.rstrip('/')}/{owner}/{repo}/raw/branch/{urllib.parse.quote(branch)}/{urllib.parse.quote(name)}"
            text=raw(raw_url)
            found=license_from_text(text)
            if found:
                item["license"]=found;item["license_status"]="evidence_from_forge_license_file";item["enrichment"]["license_file"]=name;break
    return item

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--input",default="data/prospection/enriched_discoveries.ndjson");ap.add_argument("--output",default="data/prospection/enriched_discoveries.ndjson");args=ap.parse_args()
    src=Path(args.input);out=Path(args.output);tmp=out.with_suffix(".tmp.ndjson");counts={"gitlab":0,"forgejo":0,"unchanged":0,"errors":0,"licenses_found":0}
    with src.open(encoding="utf-8") as f,tmp.open("w",encoding="utf-8") as w:
      for line in f:
        if not line.strip():continue
        x=json.loads(line); adapter=(x.get("provenance") or {}).get("adapter",""); before=x.get("license")
        if adapter=="gitlab":
          host=urllib.parse.urlparse(x.get("source_url") or x.get("url")).scheme+"://"+urllib.parse.urlparse(x.get("source_url") or x.get("url")).netloc
          x=enrich_gitlab(x,host,os.getenv("LEONES_GITLAB_TOKEN") or os.getenv("LEONES_FRAMAGIT_TOKEN"));counts["gitlab"]+=1
        elif adapter=="forgejo":
          base=x.get("source_url") or (urllib.parse.urlparse(x.get("url")).scheme+"://"+urllib.parse.urlparse(x.get("url")).netloc)
          x=enrich_forgejo(x,base);counts["forgejo"]+=1
        else:counts["unchanged"]+=1
        if x.get("license") and x.get("license")!=before:counts["licenses_found"]+=1
        if (x.get("enrichment") or {}).get("status")=="error":counts["errors"]+=1
        w.write(json.dumps(x,ensure_ascii=False)+"\n")
    tmp.replace(out)
    report={"input":str(src),"output":str(out),**counts,"note":"License values come only from source metadata or identifiable license files; unknown remains unvalidated."}
    Path("data/prospection/source_enrichment_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
