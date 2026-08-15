#!/usr/bin/env python3
"""Best-effort discovery for additional public forge/SCM instances.

Only concrete, publicly reachable instances are queried. Platform project
websites that are not repository instances remain explicitly unsupported.
"""
from __future__ import annotations
import json, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser

UA = "LEONES-Atlas-Prospection/2.8"
QUERIES = ["LLM", "inference"]
TARGETS = {
    "onedev-instance:code.onedev.io": ("onedev", "https://code.onedev.io"),
    "fossil-instance:fossil-scm.org": ("fossil", "https://fossil-scm.org/home"),
    "fossil-instance:fossilrepo.io": ("fossil", "https://fossilrepo.io"),
    "cgit-instance:git.zx2c4.com": ("cgit", "https://git.zx2c4.com/cgit"),
    "phorge-instance:phorge.it": ("phorge", "https://phorge.it"),
}

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links=[]; self.href=None; self.text=[]
    def handle_starttag(self, tag, attrs):
        if tag == "a": self.href=dict(attrs).get("href"); self.text=[]
    def handle_data(self, data):
        if self.href is not None: self.text.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.href is not None:
            self.links.append((self.href, " ".join("".join(self.text).split()))); self.href=None

def get(url, timeout=12):
    req=urllib.request.Request(url, headers={"User-Agent":UA,"Accept":"application/json,text/html;q=0.9,*/*;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8","replace"), r.status

def row(source, adapter, base, name, url, query, kind="software", description=""):
    return {"type":kind,"name":name,"url":url,"description":description,"source":source,"source_url":base,"evidence_url":url,"license":"","license_status":"unvalidated","observed_at":datetime.now(timezone.utc).isoformat(),"query":query,"publication_status":"discovered","provenance":{"adapter":adapter,"source_id":source}}

def onedev(source, base, q):
    urls=[base+"/projects?query="+urllib.parse.quote(q), base+"/projects?search="+urllib.parse.quote(q)]
    for u in urls:
        try:
            html,status=get(u); p=Links(); p.feed(html); out=[]; seen=set()
            for href,label in p.links:
                if not label or href in seen: continue
                if href.startswith("/onedev/") or "/projects/" in href:
                    seen.add(href); out.append(row(source,"onedev",base,label,urllib.parse.urljoin(base,href),q))
                    if len(out)>=20: break
            if out:return out,status
        except Exception:pass
    return [],200

def fossil(source, base, q):
    for u in [base+"/search?search="+urllib.parse.quote(q),base+"/search?searchterm="+urllib.parse.quote(q)]:
        try:
            html,status=get(u); p=Links(); p.feed(html); out=[]; seen=set()
            for href,label in p.links:
                if not label or href in seen: continue
                if any(x in href for x in ("/home/","/projects/","/code/")):
                    seen.add(href); out.append(row(source,"fossil",base,label,urllib.parse.urljoin(base,href),q))
                    if len(out)>=20: break
            if out:return out,status
        except Exception:pass
    return [],200

def cgit(source, base, q):
    u=base+"/?q="+urllib.parse.quote(q)+"&qt=grep"
    try:
        html,status=get(u); p=Links(); p.feed(html); out=[]; seen=set()
        for href,label in p.links:
            if not label or href in seen: continue
            if href.startswith("/") and href.count("/")==2:
                seen.add(href); out.append(row(source,"cgit",base,label,urllib.parse.urljoin(base,href),q))
                if len(out)>=20:break
        return out,status
    except Exception:return [],0

def phorge(source, base, q):
    for u in [base+"/source/",base+"/maniphest/"]:
        try:
            html,status=get(u); p=Links(); p.feed(html); out=[]; seen=set(); needle=q.lower()
            for href,label in p.links:
                if not label or href in seen: continue
                if needle in (label+" "+href).lower() and ("/source/" in href or "/maniphest/" in href):
                    seen.add(href); out.append(row(source,"phorge",base,label,urllib.parse.urljoin(base,href),q))
            if out:return out,status
        except Exception:pass
    return [],200

FN={"onedev":onedev,"fossil":fossil,"cgit":cgit,"phorge":phorge}

def main():
    out=Path("data/prospection/additional_forge_discoveries.ndjson"); report=Path("data/prospection/additional_forge_report.json"); fed=Path("data/prospection/federated_discoveries.ndjson"); out.parent.mkdir(parents=True,exist_ok=True)
    unique={}; stats=Counter(); errors=[]
    for source,(adapter,base) in TARGETS.items():
        fn=FN[adapter]
        for q in QUERIES:
            try:
                rows,status=fn(source,base,q)
                for r in rows: unique[r["url"]]=r
                stats[source]+=len(rows)
            except Exception as exc: errors.append({"source_id":source,"query":q,"status":"error","error_type":type(exc).__name__,"message":str(exc)[:300]})
    with out.open("w",encoding="utf-8") as f:
        for r in unique.values():f.write(json.dumps(r,ensure_ascii=False)+"\n")
    # Merge into the federation before the normal discovery merge/classifier.
    existing=set()
    if fed.exists():
        for line in fed.read_text(encoding="utf-8").splitlines():
            try:
                x=json.loads(line); existing.add(x.get("url") or f"{x.get('source')}:{x.get('name')}")
            except Exception: pass
    with fed.open("a",encoding="utf-8") as f:
        for r in unique.values():
            key=r["url"] or f"{r['source']}:{r['name']}"
            if key not in existing:
                f.write(json.dumps(r,ensure_ascii=False)+"\n"); existing.add(key)
    data={"generated_at":datetime.now(timezone.utc).isoformat(),"sources":len(TARGETS),"raw_results_by_source":dict(stats),"unique_discoveries":len(unique),"merged_into_federation":sum(1 for r in unique.values() if (r["url"] or f"{r['source']}:{r['name']}") in existing),"errors":errors,"active_adapters":sorted(TARGETS),"note":"Only concrete public instances are queried; platform websites without repository instances remain outside this adapter."}
    report.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");print(json.dumps(data,ensure_ascii=False,indent=2))

if __name__=="__main__":main()
