#!/usr/bin/env python3
"""Generate recommendation hypotheses from external empirical evidence.

This script deliberately produces hypotheses, not verified recommendations.
It reads the evidence register and emits a review queue for Atlas.
"""
from __future__ import annotations
import csv, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "data/prospection/atlas_external_evidence.csv"
OUT = ROOT / "data/prospection/atlas_hypotheses.csv"

KEYS = {
    "tokens": re.compile(r"(\d+(?:\.\d+)?)\s*tok/s", re.I),
    "gpu": re.compile(r"(\d+(?:\.\d+)?)\s*GB\s*(?:card|GPU|VRAM)", re.I),
    "quant": re.compile(r"\b(Q[2-8](?:_[A-Z0-9_]+)?)\b", re.I),
}

def main():
    if not SRC.exists():
        OUT.write_text("source,claim,hypothesis,status\n", encoding="utf-8")
        return
    with SRC.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    out=[]
    for r in rows:
        claim = r.get("claim", "") or r.get("text", "") or ""
        src = r.get("source", "") or r.get("source_type", "")
        low = claim.lower()
        h = None
        if KEYS["tokens"].search(claim) and ("16 gb" in low or KEYS["gpu"].search(claim)):
            h = "Candidate for interactive local inference on similarly sized GPU; reproduce on LEONES hardware before recommendation."
        elif "bigcodebench" in low or "coding index" in low:
            h = "Candidate coding model; use score as quality hypothesis, not as local throughput evidence."
        elif "precision" in low or "quant" in low:
            h = "Candidate precision/quality trade-off; compare CABE and RULA at the same hardware target."
        if h:
            out.append({"source":src,"claim":claim,"hypothesis":h,"status":"hypothesis"})
    fields=["source","claim","hypothesis","status"]
    with OUT.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(out)

if __name__ == "__main__":
    main()
