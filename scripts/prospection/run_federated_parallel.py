#!/usr/bin/env python3
"""Run federated discovery concurrently, one isolated source per worker.

The existing source adapters remain the single implementation of discovery.
This wrapper isolates each source in its own temporary registry/output so a slow
or broken source cannot block the complete run or corrupt another source's data.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_one(source: dict, queries: int, forge_instances: Path, timeout: int):
    source_id = source["id"]
    with tempfile.TemporaryDirectory(prefix="leones-source-") as td:
        td = Path(td)
        registry = td / "registry.json"
        output = td / "result.ndjson"
        registry.write_text(json.dumps({"version": "worker", "sources": [source]}, ensure_ascii=False), encoding="utf-8")
        # The adapter reads the shared discovery file from the repository. If the
        # file exists, leave it in place; it is read-only during this phase.
        cmd = [sys.executable, str(ROOT / "scripts/prospection/run_federated_discovery.py"),
               "--registry", str(registry), "--output", str(output), "--queries", str(queries)]
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout,
                                  env=os.environ.copy())
            rows = []
            if output.exists():
                rows = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines() if line.strip()]
            report = {}
            report_path = output.parent / "federated_discovery_report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
            return {"source_id": source_id, "returncode": proc.returncode, "rows": rows,
                    "report": report, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}
        except subprocess.TimeoutExpired as exc:
            return {"source_id": source_id, "returncode": 124, "rows": [], "report": {},
                    "stdout": (exc.stdout or "")[-2000:] if isinstance(exc.stdout, str) else "",
                    "stderr": "source timeout"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", default="scripts/prospection/sources_registry.json")
    ap.add_argument("--output", default="data/prospection/federated_discoveries.ndjson")
    ap.add_argument("--queries", type=int, default=2)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=90)
    args = ap.parse_args()

    registry = json.loads((ROOT / args.registry).read_text(encoding="utf-8"))
    sources = registry.get("sources", [])
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)

    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run_one, source, args.queries, ROOT / "data/prospection/forge_instances.ndjson", args.timeout)
                   for source in sources]
        for future in as_completed(futures):
            results.append(future.result())

    unique = {}
    source_stats = {}
    failures = []
    for result in results:
        sid = result["source_id"]
        rows = result["rows"]
        for row in rows:
            key = row.get("url") or f"{row.get('source')}:{row.get('name')}"
            unique[key] = row
        report = result.get("report", {})
        source_stats[sid] = len(rows)
        if result["returncode"] != 0:
            failures.append({"source_id": sid, "status": "timeout" if result["returncode"] == 124 else "error",
                             "returncode": result["returncode"], "stderr": result.get("stderr", "")})

    with out.open("w", encoding="utf-8") as handle:
        for row in unique.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    summary = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "sources_total": len(sources),
        "sources_completed": len(sources) - len(failures),
        "sources_failed_or_timed_out": len(failures),
        "raw_results_by_source": dict(sorted(source_stats.items())),
        "unique_discoveries": len(unique),
        "failures": failures,
        "workers": args.workers,
        "per_source_timeout_seconds": args.timeout,
        "queries": args.queries,
        "output": str(args.output),
        "note": "Each source runs in an isolated worker. A source failure is recorded and does not block the other sources. License Gate remains independent."
    }
    (out.parent / "federated_discovery_report.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    # Discovery degradation is observable but does not make the whole daily run fail.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
