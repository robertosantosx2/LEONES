#!/usr/bin/env python3
"""Build research catalog from curated Markdown and recursive Git inventory."""
import argparse,json,re,subprocess
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[2]
INDEX=ROOT/"docs/research/RESEARCH-PROJECTS-INDEX.md"
DATA=ROOT/"web/data/research-projects.json"
PAGE=ROOT/"web/investigacion.html"
REPO="https://github.com/robertosantosx2/LEONES"
def clean(s):
 s=re.sub(r"\*\*(.*?)\*\*",r"\1",s);s=re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",s);return s.replace(chr(96),"").strip()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--check",action="store_true");args=ap.parse_args()
 paths=sorted(x.decode() for x in subprocess.run(["git","ls-files","-z"],cwd=ROOT,check=True,capture_output=True).stdout.split(b"\0") if x)
 category="Investigación";items=[]
 for line in INDEX.read_text(encoding="utf-8").splitlines():
  h=re.match(r"^##\s+\d+\.\s+(.+)",line)
  if h:category=h.group(1);continue
  if not line.startswith("|") or line.startswith("|---"):continue
  c=[x.strip() for x in line.strip("|").split("|")]
  if len(c)<5 or c[0] in ("Proyecto","Línea"):continue
  m=re.search(r"\]\(([^)]+)\)",c[1]);target=m.group(1) if m else ""
  if target and not target.startswith(("http://","https://")):
   parts=[]
   for x in PurePosixPath("docs/research").joinpath(target).parts:
    if x=="..":
     if parts:parts.pop()
    elif x!=".":parts.append(x)
   target="/".join(parts);url=f"{REPO}/blob/main/{target}"
  else:url=target or REPO;target=""
  items.append({"name":clean(c[0]),"category":category,"path":target,"url":url,"description":clean(c[2]),"potential":clean(c[3]),"status":clean(c[4])})
 if not items:raise SystemExit("Empty research catalog; refusing publication")
 roots=("research/","docs/research/","docs/subprojects/","projects/","benchmarks/agentic/","finetuning/","quant/")
 readmes=[p for p in paths if p.lower().endswith(("readme.md","readme.rst","readme.txt")) and p.startswith(roots)]
 known={x["path"] for x in items if x["path"]}
 pending=[{"path":p,"url":f"{REPO}/blob/main/{p}"} for p in readmes if p not in known and p!="docs/research/RESEARCH-PROJECTS-INDEX.md"]
 data={"title":"LEONES · Observatorio de Investigación","generated_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),"source":"docs/research/RESEARCH-PROJECTS-INDEX.md","scan":"Recorrido recursivo del árbol Git (git ls-files).","repository":{"tracked_files":len(paths),"research_readmes":len(readmes)},"items":items,"unclassified_readmes":pending,"publication_is_not_approval":True,"automatic_priority_changes":False}
 outputs={DATA:json.dumps(data,ensure_ascii=False,indent=2)+"\n"}
 drift=[]
 for p,v in outputs.items():
  if args.check:
   if not p.exists() or p.read_text(encoding="utf-8")!=v:drift.append(str(p))
  else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(v,encoding="utf-8")
 if drift:raise SystemExit("Stale generated data: "+", ".join(drift))
 print(f"{len(items)} catalog entries; {len(paths)} tracked files scanned; {len(readmes)} research README files; {len(pending)} unclassified.")
if __name__=="__main__":main()
