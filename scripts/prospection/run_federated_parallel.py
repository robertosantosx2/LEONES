#!/usr/bin/env python3
"""Run federated discovery concurrently with one isolated worker per source/instance."""

from __future__ import annotations
import argparse, json, os, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def run_one(
    source: dict | None, queries: int, timeout: int, only_instances: bool = False
):
    label = source["id"] if source else "discovered-forges"
    with tempfile.TemporaryDirectory(prefix="leones-source-") as td:
        td = Path(td)
        registry = td / "registry.json"
        output = td / "result.ndjson"
        registry.write_text(
            json.dumps(
                {"version": "worker", "sources": [source] if source else []},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        cmd = [
            sys.executable,
            str(ROOT / "scripts/prospection/run_federated_discovery.py"),
            "--registry",
            str(registry),
            "--output",
            str(output),
            "--queries",
            str(queries),
        ]
        if only_instances:
            cmd.append("--only-discovered-instances")
        else:
            cmd.append("--skip-discovered-instances")
        try:
            proc = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy(),
            )
            rows = []
            if output.exists():
                rows = [
                    json.loads(line)
                    for line in output.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                ]
            report = {}
            report_path = output.parent / "federated_discovery_report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
            return {
                "source_id": label,
                "returncode": proc.returncode,
                "rows": rows,
                "report": report,
                "stdout": proc.stdout[-4000:],
                "stderr": proc.stderr[-4000:],
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "source_id": label,
                "returncode": 124,
                "rows": [],
                "report": {},
                "stdout": (exc.stdout or "")[-2000:]
                if isinstance(exc.stdout, str)
                else "",
                "stderr": "source timeout",
            }


def load_instances():
    path = ROOT / "data/prospection/forge_instances.ndjson"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            url = json.loads(line).get("url", "").rstrip("/")
            if url:
                out.append(url)
        except ValueError:
            continue
    env_instances = [
        x.strip().rstrip("/")
        for x in os.getenv("LEONES_FORGEJO_INSTANCES", "").split(",")
        if x.strip()
    ]
    return list(dict.fromkeys(out + env_instances))


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
    instances = load_instances()
    # Codeberg is already a registry source; avoid querying it twice.
    instances = [x for x in instances if "codeberg.org" not in x]
    tasks = [(source, False) for source in sources] + [
        (None, True) for _ in ([instances] if instances else [])
    ]
    results = []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [
            pool.submit(run_one, source, args.queries, args.timeout, only_instances)
            for source, only_instances in tasks
        ]
        for future in as_completed(futures):
            results.append(future.result())
    unique = {}
    source_stats = {}
    failures = []
    for result in results:
        sid = result["source_id"]
        for row in result["rows"]:
            key = row.get("url") or f"{row.get('source')}:{row.get('name')}"
            unique[key] = row
        source_stats[sid] = len(result["rows"])
        if result["returncode"] != 0:
            failures.append(
                {
                    "source_id": sid,
                    "status": "timeout" if result["returncode"] == 124 else "error",
                    "returncode": result["returncode"],
                    "stderr": result.get("stderr", ""),
                }
            )
    out = ROOT / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for row in unique.values():
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary = {
        "generated_at": __import__("datetime")
        .datetime.now(__import__("datetime").timezone.utc)
        .isoformat(),
        "sources_total": len(sources) + (1 if instances else 0),
        "registered_sources": len(sources),
        "discovered_instance_batch": len(instances),
        "sources_completed": len(sources) + (1 if instances else 0) - len(failures),
        "sources_failed_or_timed_out": len(failures),
        "raw_results_by_source": dict(sorted(source_stats.items())),
        "unique_discoveries": len(unique),
        "failures": failures,
        "workers": args.workers,
        "per_worker_timeout_seconds": args.timeout,
        "queries": args.queries,
        "output": str(args.output),
        "note": "Registered sources and discovered Forgejo/Gitea instances run in isolated workers. A source failure does not block the other workers. License Gate remains independent.",
    }
    (out.parent / "federated_discovery_report.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
