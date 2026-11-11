#!/usr/bin/env python3
"""Record reproducible build provenance for one vendored inference engine."""
from __future__ import annotations
import argparse, datetime, hashlib, json, os, pathlib, platform, shutil, subprocess, re

ROOT=pathlib.Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def command_version(cmd):
    try:
        p=subprocess.run(cmd,text=True,capture_output=True,timeout=15)
        return {"argv":cmd,"returncode":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
    except Exception as e: return {"argv":cmd,"error":str(e)}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--engine",required=True)
    ap.add_argument("--binary",required=True)
    ap.add_argument("--build-command",required=True,help="Human-readable exact build command")
    ap.add_argument("--build-log",required=True)
    ap.add_argument("--compiler",action="append",default=[],help="Compiler version command, repeatable; e.g. rustc --version")
    ap.add_argument("--feature",action="append",default=[])
    ap.add_argument("--backend",default="unknown")
    ap.add_argument("--output",help="Output JSON path")
    a=ap.parse_args()
    binary=pathlib.Path(a.binary).expanduser().resolve()
    log=pathlib.Path(a.build_log).expanduser().resolve()
    if not binary.is_file() or not log.is_file(): ap.error("binary and build log must exist")
    out=pathlib.Path(a.output) if a.output else ROOT/"artifacts"/"engine-builds"/a.engine/(datetime.datetime.now().strftime("%Y%m%d-%H%M%S")+".json")
    out.parent.mkdir(parents=True,exist_ok=True)
    source_meta=ROOT/"third_party"/"engines"/a.engine/"SOURCE.json"
    source=json.loads(source_meta.read_text()) if source_meta.is_file() else None
    data={
      "schema_version":1,"captured_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "engine_id":a.engine,"source":source,"binary":{"path":str(binary),"sha256":sha(binary),"size_bytes":binary.stat().st_size},
      "build":{"command":a.build_command,"log_path":str(log),"log_sha256":sha(log),"features":a.feature,"backend":a.backend},
      "toolchain":{"platform":platform.platform(),"python":platform.python_version(),"compilers":[command_version(x.split()) for x in a.compiler]},
      "environment":{k:("<redacted>" if re.search(r"(TOKEN|KEY|SECRET|PASSWORD)",k,re.I) else v) for k,v in os.environ.items() if k in ("PATH","LD_LIBRARY_PATH","CC","CXX","CFLAGS","CXXFLAGS") or k.startswith(("CUDA","HIP","TENSORFOLD","LLAMA","TF_","RUST","CMAKE"))},
    }
    out.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n")
    print(out)
if __name__=="__main__": main()
