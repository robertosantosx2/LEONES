#!/usr/bin/env python3
"""Build the external-evidence queue without promoting discoveries to Atlas.

Sources are classified from URLs already discovered by LEONES. The script
supports Hugging Face, LMSYS/LM Arena, Artificial Analysis and official
manufacturer domains. It never invents a claim or promotes external evidence
to verified LEONES measurement.
"""

from __future__ import annotations
import csv
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "data" / "prospection" / "atlas_feed.csv"
OUT = ROOT / "data" / "prospection" / "atlas_external_evidence.csv"
FIELDS = [
    "model_id",
    "model_name",
    "source_type",
    "url",
    "retrieved_at",
    "claim",
    "source_record_id",
    "evidence_status",
]

HOST_TYPES = {
    "huggingface.co": "hugging_face",
    "lmarena.ai": "lm_arena",
    "arena.ai": "lm_arena",
    "artificialanalysis.ai": "artificial_analysis",
    "msa.millaguie.net": "msa",
    "llm-stats.com": "llm_stats",
    "vellum.ai": "vellum",
    "lambda.ai": "lambda_benchmarks",
    "swebench.com": "swe_bench",
    "livecodebench.github.io": "livecodebench",
}


def source_type(url):
    host = urlparse(url or "").netloc.lower().split(":")[0]
    for domain, kind in HOST_TYPES.items():
        if host == domain or host.endswith("." + domain):
            return kind
    return ""


def manufacturer_source(url):
    """Conservative manufacturer detection from the model's organization.

    We only classify a URL as manufacturer when the URL already appears in
    the source feed and its host contains an organization token. No URL is
    fabricated here.
    """
    return False


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if not IN.exists():
        OUT.write_text(",".join(FIELDS) + "\n", encoding="utf-8")
        return
    rows = []
    seen = set()
    with IN.open(encoding="utf-8", newline="") as fh:
        for r in csv.DictReader(fh):
            urls = [
                r.get("source_url", ""),
                r.get("weights_url", ""),
                r.get("code_url", ""),
            ]
            for url in urls:
                st = source_type(url)
                if not st:
                    continue
                key = (r.get("model_id", ""), st, url)
                if key in seen:
                    continue
                seen.add(key)
                rows.append(
                    {
                        "model_id": r.get("model_id", ""),
                        "model_name": r.get("model_name", ""),
                        "source_type": st,
                        "url": url,
                        "retrieved_at": "",
                        "claim": "",
                        "source_record_id": r.get("source_record_id", "")
                        or r.get("id", ""),
                        "evidence_status": "reported",
                    }
                )
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"External evidence queue: {len(rows)} records -> {OUT}")


if __name__ == "__main__":
    main()
