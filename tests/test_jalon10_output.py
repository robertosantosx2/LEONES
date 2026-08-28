from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/jalon10_output.py"

def base():
    return {"recommendation_id":"rec-12345678","entity":"model-x","decision_ref":"decision-1","evidence_refs":["evidence-1"],"status":"recommend","rationale":"supported","unknowns":[],"next_action":"recommend"}

def run(tmp, data):
    src=tmp/"r.json"; dst=tmp/"o.json"; src.write_text(json.dumps(data), encoding="utf-8")
    return subprocess.run([sys.executable,str(SCRIPT),str(src),str(dst)],capture_output=True,text=True), dst

def test_faithful_output(tmp_path):
    p=base(); r,out=run(tmp_path,p)
    assert r.returncode==0, r.stderr
    got=json.loads(out.read_text())
    for k in ("entity","status","rationale","unknowns","next_action","decision_ref","evidence_refs"):
        assert got[k]==p[k]
    assert got["recommendation_ref"]==p["recommendation_id"]

def test_trace_is_forwarded(tmp_path):
    p=base(); p["trace_ref"]="trace-1"; r,out=run(tmp_path,p)
    assert r.returncode==0
    assert json.loads(out.read_text())["trace_ref"]=="trace-1"

def test_parallel_metric_is_rejected(tmp_path):
    p=base(); p["score"]=0.9; r,_=run(tmp_path,p)
    assert r.returncode!=0

def test_output_has_no_parallel_metric(tmp_path):
    r,out=run(tmp_path,base()); assert r.returncode==0
    assert not {"score","ranking_score","estimated_tps","tokens_per_second_estimate"}.intersection(json.loads(out.read_text()))
