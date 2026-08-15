#!/usr/bin/env python3
"""Collect externally published empirical evidence without promoting it.

Network access is intentionally optional. The collector uses public URLs and
records source metadata; it never marks external claims as LEONES-verified.
"""
from __future__ import annotations
import csv, datetime as dt, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"
SITES = ROOT / "atlas/empirical-evidence-sites.md"
FIELDS = ["model_id","model_name","source_type","url","retrieved_at","claim","source_record_id","evidence_status"]

URLS = {
    "hugging_face": "https://huggingface.co/spaces/open-llm-leaderboard/open_llm_leaderboard",
    "msa": "https://msa.millaguie.net/",
    "lm_arena": "https://chat.lmsys.org/",
    "artificial_analysis": "https://artificialanalysis.ai/",
}

def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent":"LEONES-Atlas/0.2"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "ignore")

def extract_claims(source: str, html: str):
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text).strip()
    patterns = [
        r"[^.]{0,180}\d+(?:\.\d+)?\s*tok/s[^.]{0,180}",
        r"[^.]{0,180}\d+(?:\.\d+)?\s*%[^.]{0,180}",
        r"[^.]{0,180}(?:GPQA|MMLU(?:-Pro)?|SWE-bench|LiveCodeBench|BigCodeBench)[^.]{0,180}",
    ]
    seen = set()
    for p in patterns:
        for m in re.finditer(p, text, re.I):
            claim = m.group(0).strip()
            if claim and claim not in seen:
                seen.add(claim)
                yield claim

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for source, url in URLS.items():
        try:
            html = fetch(url)
        except Exception as exc:
            print(f"WARN {source}: {exc}")
            continue
        for i, claim in enumerate(extract_claims(source, html), 1):
            rows.append({
                "model_id":"", "model_name":"", "source_type":source,
                "url":url, "retrieved_at":now, "claim":claim,
                "source_record_id":f"{source}:{i}", "evidence_status":"reported"
            })
    existing = []
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f: existing = list(csv.DictReader(f))
    seen = {(r.get("source_type"), r.get("url"), r.get("claim")) for r in existing}
    for r in rows:
        if (r["source_type"], r["url"], r["claim"]) not in seen:
            existing.append(r); seen.add((r["source_type"], r["url"], r["claim"]))
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w=csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(existing)
    print(f"External empirical evidence: {len(rows)} newly observed claims; {len(existing)} total")

if __name__ == "__main__": main()
