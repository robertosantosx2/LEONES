#!/usr/bin/env python3
"""Daily LEONES prospection -> Atlas staging pipeline.

Discovery is deliberately separated from publication. This script consumes
classified newline-delimited JSON discoveries, normalizes/deduplicates them,
applies the software-license OSI gate, and separates Atlas candidates from
records requiring review. It never promotes an unverified discovery directly
to the public Atlas.
"""

from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

SOFTWARE_TYPES = {"runtime", "agent", "skill", "harness", "tool", "framework"}
OSI_LICENSES = {
    "Apache-2.0",
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "MPL-2.0",
    "LGPL-2.1-only",
    "LGPL-3.0-only",
    "GPL-2.0-only",
    "GPL-3.0-only",
    "AGPL-3.0-only",
    "EPL-2.0",
    "CDDL-1.0",
}


def norm(s):
    return " ".join(str(s or "").strip().split())


def key(x):
    return hashlib.sha256(
        (
            norm(x.get("type", x.get("category")))
            + "|"
            + norm(x.get("name"))
            + "|"
            + norm(x.get("url"))
        )
        .lower()
        .encode()
    ).hexdigest()[:16]


def license_gate(x):
    if x.get("type") not in SOFTWARE_TYPES:
        return "not-applicable"
    lic = norm(x.get("license") or x.get("license_spdx"))
    if lic in OSI_LICENSES:
        return "osi-compatible"
    if not lic:
        return "unvalidated"
    return "non-osi-or-unverified"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/prospection/classified_discoveries.ndjson")
    ap.add_argument("--output", default="data/prospection/atlas_review_queue.ndjson")
    ap.add_argument("--candidates", default="data/prospection/atlas_candidates.ndjson")
    args = ap.parse_args()
    src, out, candidates = Path(args.input), Path(args.output), Path(args.candidates)
    out.parent.mkdir(parents=True, exist_ok=True)
    seen, rows, candidate_rows = set(), [], []
    now = datetime.now(timezone.utc).isoformat()
    if src.exists():
        for line in src.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            x = json.loads(line)
            x = {k: (norm(v) if isinstance(v, str) else v) for k, v in x.items()}
            x["discovery_id"] = x.get("discovery_id") or key(x)
            x["discovered_at"] = x.get("discovered_at") or now
            x["license_gate"] = license_gate(x)
            x["source"] = x.get("source") or x.get("url")
            if x["discovery_id"] in seen:
                continue
            seen.add(x["discovery_id"])
            if x["license_gate"] == "osi-compatible":
                x["publication_status"] = "atlas_candidate"
                candidate_rows.append(x)
            else:
                x["publication_status"] = "review"
                rows.append(x)
    out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in rows)
        + ("\n" if rows else ""),
        encoding="utf-8",
    )
    candidates.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in candidate_rows)
        + ("\n" if candidate_rows else ""),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "discovered": len(rows) + len(candidate_rows),
                "atlas_candidates": len(candidate_rows),
                "review_queue": len(rows),
                "review_file": str(out),
                "candidate_file": str(candidates),
                "generated_at": now,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
