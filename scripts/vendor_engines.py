#!/usr/bin/env python3
"""Vendor pinned inference-engine source repositories into LEONES.

Keeps a full Git mirror (history/refs/objects) plus a clean source checkout.
Does not build or execute upstream code. Requires git; rsync is optional.
"""
from __future__ import annotations
import argparse, datetime, hashlib, json, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "configs/engines.registry.json"
DEST = ROOT / "third_party/engines"

def git(args, cwd=None, check=True):
    p = subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True)
    if check and p.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed ({p.returncode}): {p.stderr.strip()}")
    return p.stdout.strip()

def digest(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def copy_tree(src,dst):
    if dst.exists(): shutil.rmtree(dst)
    shutil.copytree(src,dst,symlinks=True,ignore=shutil.ignore_patterns(".git"))

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine",action="append",help="engine id; repeatable; default all with repository URLs")
    ap.add_argument("--refresh",action="store_true",help="fetch new refs before resolving configured ref")
    ap.add_argument("--ref",action="append",default=[],help="override ref as id=tag/branch/commit")
    args=ap.parse_args()
    registry=json.loads(REGISTRY.read_text())
    overrides=dict(x.split("=",1) for x in args.ref)
    selected=set(args.engine or [])
    entries=[e for e in registry["engines"] if (not selected or e["id"] in selected)]
    if not entries: ap.error("no matching engine ids")
    report={"schema_version":1,"created_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"engines":[]}
    DEST.mkdir(parents=True,exist_ok=True)
    failures=0
    for e in entries:
        eid=e["id"]; url=e.get("repository")
        if not url:
            report["engines"].append({"id":eid,"status":"SOURCE_URL_REQUIRED","detail":e.get("notes")})
            failures+=1; continue
        base=DEST/eid; mirror=base/"git-mirror.git"; source=base/"source"
        base.mkdir(parents=True,exist_ok=True)
        try:
            if not mirror.exists():
                git(["clone","--mirror",url,str(mirror)])
            elif args.refresh:
                git(["--git-dir",str(mirror),"remote","update","--prune"])
            ref=overrides.get(eid,e.get("default_ref") or "HEAD")
            commit=git(["--git-dir",str(mirror),"rev-parse",f"{ref}^{{commit}}"])
            with tempfile.TemporaryDirectory(prefix=f"leones-{eid}-") as td:
                checkout=pathlib.Path(td)/"checkout"
                git(["clone","--no-checkout",str(mirror),str(checkout)])
                git(["checkout","--detach",commit],cwd=checkout)
                submodules=git(["submodule","status","--recursive"],cwd=checkout,check=False)
                subproc=subprocess.run(["git","submodule","update","--init","--recursive"],cwd=checkout,text=True,capture_output=True)
                if subproc.returncode:
                    raise RuntimeError("submodule update failed: "+subproc.stderr.strip())
                lfs="not-installed"
                if shutil.which("git-lfs"):
                    lfs=git(["lfs","pull"],cwd=checkout,check=False) or "git-lfs pull completed"
                copy_tree(checkout,source)
                # Capture exact build-relevant metadata and submodule revisions.
                meta={
                  "engine_id":eid,"display_name":e.get("display_name"),"repository":url,
                  "ref_requested":ref,"commit":commit,"vendored_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "git_mirror":"git-mirror.git","source_tree":"source",
                  "submodule_status":submodules,"git_lfs":lfs,
                  "license_files":[p.name for p in source.iterdir() if p.is_file() and p.name.upper().startswith(("LICENSE","COPYING","NOTICE","PATENTS","TRADEMARKS"))],
                  "source_status":"PINNED_SNAPSHOT"
                }
                (base/"SOURCE.json").write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
            report["engines"].append({"id":eid,"status":"VENDORED","commit":commit,"path":str(base.relative_to(ROOT))})
            print(f"[OK] {eid}: {commit}")
        except Exception as ex:
            failures+=1
            report["engines"].append({"id":eid,"status":"ERROR","error":str(ex)})
            print(f"[ERROR] {eid}: {ex}",file=sys.stderr)
    report_path=DEST/"VENDOR_REPORT.json"
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print(f"Report: {report_path.relative_to(ROOT)}")
    if failures: sys.exit(2)

if __name__=="__main__": main()
