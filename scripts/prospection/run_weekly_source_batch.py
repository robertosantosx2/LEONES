#!/usr/bin/env python3
"""Extract each registered source once per week, distributed across 7 days.

The assignment is deterministic from the registry order. Each day runs only its
assigned sources, independently, so a slow source cannot delay the other days.
"""
from __future__ import annotations
import argparse, json, subprocess, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def run_source(source: dict, queries: int, timeout: int):
    import tempfile
    with tempfile.TemporaryDirectory(prefix="leones-weekly-source-") as td:
        td = Path(td)
        registry = td / "registry.json"
        output = td / "result.ndjson"
        registry.write_text(json.dumps({"version": "weekly-worker", "sources": [source]}, ensure_ascii=False), encoding="utf-8")
        cmd = [sys.executable, str(ROOT / "scripts/prospection/run_federated_discovery.py"),
               "--registry", str(registry), "--output", str(output), "--queries", str(queries),
               "--skip-discovered-instances"]
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            rows = [json.loads(x) for x in output.read_text(encoding="utf-8").splitlines() if x.strip()] if output.exists() else []
            return {"source_id": source["id"], "rows": rows, "returncode": proc.returncode,
                    "stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]}
        except subprocess.TimeoutExpired:
            return {"source_id": source["id"], "rows": [], "returncode": 124,
                    "stderr": "source extraction timeout", "stdout": ""}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="scripts/prospection/sources_registry.json")
    ap.add_argument("--day", default="auto", choices=["auto", *DAYS])
    ap.add_argument("--queries", type=int, default=2)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--timeout", type=int, default=75)
    ap.add_argument("--output-dir", default="data/prospection/weekly_sources")
    args = ap.parse_args()

    registry = json.loads((ROOT / args.registry).read_text(encoding="utf-8"))
    sources = registry.get("sources", [])
    now = datetime.now(timezone.utc)
    day_index = now.weekday() if args.day == "auto" else DAYS[args.day]
    assigned = [s for i, s in enumerate(sources) if i % 7 == day_index]

    results = []
    with ThreadPoolExecutor(max_workers=max(1, min(args.workers, len(assigned) or 1))) as pool:
        futures = [pool.submit(run_source, source, args.queries, args.timeout) for source in assigned]
        for future in as_completed(futures):
            results.append(future.result())

    unique = {}
    stats = {}
    failures = []
    for result in results:
        sid = result["source_id"]
        stats[sid] = len(result["rows"])
        for row in result["rows"]:
            key = row.get("url") or f"{row.get('source')}:{row.get('name')}"
            unique[key] = row
        if result["returncode"] != 0:
            failures.append({"source_id": sid, "status": "timeout" if result["returncode"] == 124 else "error",
                             "returncode": result["returncode"], "message": result["stderr"]})

    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    date_tag = now.strftime("%Y-%m-%d")
    out = out_dir / f"sources-{date_tag}.ndjson"
    with out.open("w", encoding="utf-8") as f:
        for row in unique.values():
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    assignment = [{"id": s["id"], "name": s.get("name"), "day": i % 7} for i, s in enumerate(sources)]
    report = {
        "generated_at": now.isoformat(), "day": day_index, "day_name": now.strftime("%A").lower(),
        "sources_assigned": [s["id"] for s in assigned], "sources_total": len(sources),
        "sources_completed": len(assigned) - len(failures), "sources_failed": len(failures),
        "raw_results_by_source": dict(sorted(stats.items())), "unique_discoveries": len(unique),
        "failures": failures, "queries": args.queries, "workers": args.workers,
        "per_source_timeout_seconds": args.timeout, "weekly_assignment": assignment,
        "output": str(out), "cadence": "weekly-per-source"
    }
    (out_dir / "weekly_source_schedule.json").write_text(json.dumps({"generated_at": now.isoformat(), "sources": assignment}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / f"report-{date_tag}.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
