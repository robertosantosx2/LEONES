#!/usr/bin/env python3
"""Conservatively ingest model discoveries and canonical repository evidence.

The Atlas keeps model identity separate from the hosting forge. A discovery
may mention a repository, but the repository URL must be reconstructed only
when the source forge and a plausible ``owner/repository`` path are both
present. Generic forge homepages are never treated as model repositories.
"""

from __future__ import annotations
import csv, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROS = ROOT / "data" / "prospection"
OUT = PROS / "atlas_feed.csv"
REVIEW = PROS / "atlas_review_queue.csv"
FIELDS = [
    "source_file",
    "source_id",
    "model_id",
    "model_name",
    "organization",
    "release_date",
    "source_url",
    "repository_url",
    "repository_host",
    "license",
    "weights_url",
    "code_url",
    "runtime",
    "format",
    "quantization",
    "hardware_id",
    "workload",
    "jgb_level",
    "jgb_confidence",
    "quality_score",
    "tokens_per_second",
    "estimated_memory_gb",
    "context_tokens",
    "evidence_status",
    "notes",
]
FILES = ["classified_discoveries.ndjson", "additional_forge_discoveries.ndjson"]
ALIASES = {
    "id": "source_id",
    "model": "model_id",
    "model_id": "model_id",
    "name": "model_name",
    "repo": "model_id",
    "repository": "model_id",
    "repository_id": "model_id",
    "repo_name": "model_id",
    "url": "source_url",
    "evidence_url": "source_url",
    "repository_url": "repository_url",
    "repo_url": "repository_url",
    "date": "release_date",
    "license_name": "license",
    "weights": "weights_url",
    "code": "code_url",
}
FORGES = {
    "github.com": "https://github.com/",
    "gitlab.com": "https://gitlab.com/",
    "codeberg.org": "https://codeberg.org/",
    "gitea.com": "https://gitea.com/",
    "framagit.org": "https://framagit.org/",
    "pagure.io": "https://pagure.io/",
    "git.zx2c4.com": "https://git.zx2c4.com/",
    "huggingface.co": "https://huggingface.co/",
}


def flat(v):
    if isinstance(v, (str, int, float)):
        return str(v)
    if isinstance(v, list):
        return "; ".join(flat(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False, sort_keys=True)
    return ""


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def canonical_repo(base_url, model_id):
    host = host_of(base_url)
    prefix = FORGES.get(host)
    if not prefix:
        return ""
    path = (model_id or "").strip().strip("/")
    # Only construct a repository URL from a plausible forge path.
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", path):
        return ""
    return prefix + path


def is_model(obj):
    typ = str(obj.get("type", "")).lower()
    cats = obj.get("categories", [])
    if isinstance(cats, str):
        cats = [cats]
    cats = {str(x).lower() for x in cats}
    return (
        typ in {"model", "llm", "language_model", "foundation_model"}
        or "models" in cats
        or "llm" in cats
    )


def normalize(obj, source):
    r = {f: "" for f in FIELDS}
    r["source_file"] = source
    for k, v in obj.items():
        target = ALIASES.get(k.strip(), k.strip())
        if target in r:
            r[target] = flat(v).strip()
    if obj.get("evidence_url"):
        r["source_url"] = flat(obj["evidence_url"]).strip()
    if not r["model_name"]:
        r["model_name"] = r["model_id"]
    if not r["model_id"]:
        r["model_id"] = r["model_name"]
    if not r["source_id"]:
        r["source_id"] = r["source_url"] or r["model_id"]
    r["repository_host"] = host_of(r["repository_url"]) or host_of(r["source_url"])
    if not r["repository_url"]:
        r["repository_url"] = canonical_repo(r["source_url"], r["model_id"])
    if r["repository_url"] and not r["source_url"]:
        r["source_url"] = r["repository_url"]
    status = (r["evidence_status"] or "").lower()
    if status not in {"verified", "confirmed"}:
        r["evidence_status"] = "discovered"
    # A generic forge homepage is not repository evidence.
    if r["source_url"] and host_of(r["source_url"]) in FORGES and r["repository_url"]:
        r["notes"] = (
            r["notes"]
            + "; canonical repository URL derived from forge + repository path"
        ).strip("; ")
    return r


def main():
    records = []
    for name in FILES:
        p = PROS / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                if is_model(obj):
                    records.append(normalize(obj, name))
            except json.JSONDecodeError:
                continue
    unique = {}
    for r in records:
        key = (
            r["repository_url"]
            or r["source_id"]
            or f"{r['model_id']}|{r['source_url']}"
        )
        if key:
            unique.setdefault(key, r)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(unique.values())
    review = [r for r in unique.values() if r["evidence_status"] != "verified"]
    with REVIEW.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(review)
    repos = sum(bool(r["repository_url"]) for r in unique.values())
    print(
        f"Atlas ingest: {len(unique)} model records; {repos} canonical repositories; {len(review)} require verification"
    )


if __name__ == "__main__":
    main()
