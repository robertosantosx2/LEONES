#!/usr/bin/env python3
"""Adapter for MSA empirical/local inference observations.

MSA observations are treated as reported empirical evidence. The adapter does
not infer hardware, runtime, or throughput when the source does not state them.
"""

from __future__ import annotations
import csv, datetime as dt, hashlib, pathlib, re, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"
URL = "https://msa.millaguie.net/"
FIELDS = [
    "model_id",
    "model_name",
    "source_type",
    "source_url",
    "retrieved_at",
    "claim",
    "metric",
    "value",
    "unit",
    "benchmark",
    "hardware",
    "runtime",
    "quantization",
    "workload",
    "evidence_status",
    "source_record_id",
    "extraction_method",
]

PATTERNS = [
    ("throughput", r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>tok(?:ens)?/s)"),
    ("memory", r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>GB)\s*(?:VRAM|RAM|memory)"),
]


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": "LEONES-Atlas/0.3"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")


def text(html):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def main():
    try:
        body = text(fetch())
    except Exception as exc:
        print(f"WARN MSA: {exc}")
        return
    now = (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    rows = []
    for metric, pattern in PATTERNS:
        for m in re.finditer(pattern, body, re.I):
            claim = m.group(0)
            context = body[max(0, m.start() - 220) : min(len(body), m.end() + 220)]
            rid = hashlib.sha256(f"msa|{URL}|{claim}".encode()).hexdigest()[:16]
            rows.append(
                {
                    "model_id": "",
                    "model_name": "",
                    "source_type": "msa",
                    "source_url": URL,
                    "retrieved_at": now,
                    "claim": context,
                    "metric": metric,
                    "value": m.group("value"),
                    "unit": m.group("unit"),
                    "benchmark": "",
                    "hardware": "",
                    "runtime": "",
                    "quantization": "",
                    "workload": "local inference",
                    "evidence_status": "reported",
                    "source_record_id": f"msa:{rid}",
                    "extraction_method": "msa_public_page",
                }
            )
    existing = []
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f:
            existing = list(csv.DictReader(f))
    seen = {r.get("source_record_id") for r in existing}
    for r in rows:
        if r["source_record_id"] not in seen:
            existing.append(r)
            seen.add(r["source_record_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing)
    print(f"MSA: {len(rows)} observations; {len(existing)} total evidence records")


if __name__ == "__main__":
    main()
