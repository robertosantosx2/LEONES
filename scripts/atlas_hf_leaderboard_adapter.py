#!/usr/bin/env python3
"""Ingest structured Hugging Face Open LLM Leaderboard evidence.

Uses the Hugging Face Dataset Viewer API rather than scraping the visual
leaderboard. Every record remains external/reported evidence and preserves
model revision, precision, benchmark metadata and retrieval time.
"""
from __future__ import annotations
import csv, datetime as dt, json, pathlib, urllib.parse, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "data/prospection/atlas_external_evidence.csv"
DATASET = "open-llm-leaderboard/results"
API = "https://datasets-server.huggingface.co/rows"
FIELDS = [
    "model_id","model_name","source_type","source_url","retrieved_at","claim",
    "metric","value","unit","benchmark","hardware","runtime","quantization",
    "workload","evidence_status","source_record_id","extraction_method",
    "model_revision","evaluation_date","precision"
]

def get_rows(offset: int = 0, length: int = 100):
    q = urllib.parse.urlencode({"dataset": DATASET, "config": "default", "split": "train", "offset": offset, "length": length})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "LEONES-Atlas/0.3"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def nested_scores(row):
    # Leaderboard results are nested dictionaries. Keep only scalar numeric
    # benchmark metrics; the complete source record remains externally traceable.
    lb = row.get("leaderboard") or {}
    if not isinstance(lb, dict): return []
    for key, value in lb.items():
        if isinstance(value, (int, float)):
            yield key, value

def normalize(raw, retrieved):
    out = []
    for item in raw.get("rows", []):
        row = item.get("row", {})
        model = row.get("model_name") or row.get("model_name_sanitized") or ""
        revision = row.get("git_hash") or ""
        evaluation_date = row.get("date") or ""
        precision = row.get("Precision") or row.get("precision") or ""
        for metric, value in nested_scores(row):
            rid = f"hf-ollm:{model}:{revision}:{metric}"
            out.append({
                "model_id": model,
                "model_name": model,
                "source_type": "hugging_face_open_llm_leaderboard",
                "source_url": "https://huggingface.co/datasets/open-llm-leaderboard/results",
                "retrieved_at": retrieved,
                "claim": f"{model}: {metric}={value}",
                "metric": metric,
                "value": value,
                "unit": "score",
                "benchmark": metric.split("_")[1] if metric.startswith("leaderboard_") else "Open LLM Leaderboard",
                "hardware": "evaluation environment documented by source",
                "runtime": "lm-evaluation-harness",
                "quantization": precision,
                "workload": "benchmark evaluation",
                "evidence_status": "reported",
                "source_record_id": rid,
                "extraction_method": "huggingface_dataset_viewer_api",
                "model_revision": revision,
                "evaluation_date": evaluation_date,
                "precision": precision,
            })
    return out

def main():
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    try:
        raw = get_rows()
    except Exception as exc:
        print(f"WARN Hugging Face Dataset Viewer API: {exc}")
        return
    new_rows = normalize(raw, now)
    existing = []
    if OUT.exists():
        with OUT.open(encoding="utf-8", newline="") as f: existing = list(csv.DictReader(f))
    seen = {r.get("source_record_id") for r in existing}
    for r in new_rows:
        if r["source_record_id"] not in seen:
            existing.append(r); seen.add(r["source_record_id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore"); w.writeheader(); w.writerows(existing)
    print(f"Hugging Face Open LLM Leaderboard: {len(new_rows)} observations; {len(existing)} total evidence records")

if __name__ == "__main__": main()
