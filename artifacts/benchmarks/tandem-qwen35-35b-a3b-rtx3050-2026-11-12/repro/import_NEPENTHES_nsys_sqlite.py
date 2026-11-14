#!/usr/bin/env python3
"""Import Nsight SQLite activities into a NEPENTHES run without modifying the source DB."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sqlite3
import uuid
from contextlib import closing
from urllib.parse import quote

from inspect_NEPENTHES_nsys_sqlite import MEMCPY_KIND, MEMORY_KIND, _columns, _strings, _tables


TABLE_SPECS = {
    "CUPTI_ACTIVITY_KIND_RUNTIME": ("runtime", {"globalTid", "nameId", "start", "end"}),
    "CUPTI_ACTIVITY_KIND_KERNEL": ("kernel", {"shortName", "start", "end"}),
    "CUPTI_ACTIVITY_KIND_MEMCPY": ("transfer", {"copyKind", "srcKind", "dstKind", "bytes", "start", "end"}),
    "CUPTI_ACTIVITY_KIND_SYNCHRONIZATION": ("sync", {"start", "end"}),
}


def connect_readonly(path: pathlib.Path):
    uri = "file:" + quote(str(path.resolve())) + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def process_map(db, tables):
    if "PROCESSES" not in tables:
        return {}
    columns = _columns(db, "PROCESSES")
    if not {"globalPid", "pid", "name"} <= columns:
        return {}
    return {int(gpid): {"pid": int(pid), "name": str(name)}
            for gpid, pid, name in db.execute("SELECT globalPid,pid,name FROM PROCESSES")}


def runtime_process(global_tid, processes):
    candidates = [gpid for gpid in processes if 0 <= global_tid - gpid < (1 << 32)]
    return processes[max(candidates)] if candidates else None


def classify_runtime(name: str) -> str:
    lowered = name.lower()
    if "synchronize" in lowered or "eventquery" in lowered or "streamwait" in lowered:
        return "sync"
    if "memcpy" in lowered or "memset" in lowered:
        return "transfer"
    return "custom"


def import_database(database: pathlib.Path, run_dir: pathlib.Path, run_id: str | None = None) -> dict:
    database = database.expanduser().resolve()
    run_dir = run_dir.expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    manifest_path = run_dir / "run_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"run manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    resolved_run_id = run_id or manifest.get("run_id")
    if not resolved_run_id:
        raise ValueError("run_id missing from manifest; supply --run-id")
    events_path = run_dir / "events" / "nsys_activity.jsonl"
    report_path = run_dir / "profiles" / "nsys_import_report.json"
    if events_path.exists() or report_path.exists():
        raise FileExistsError("Nsight import outputs already exist; choose a fresh run directory or remove outputs explicitly")

    strings = {}
    counts = {}
    imported = 0
    by_kind = {}
    with closing(connect_readonly(database)) as db:
        tables = _tables(db)
        strings = _strings(db, tables)
        processes = process_map(db, tables)
        with events_path.open("x", encoding="utf-8") as output:
            for table, (category, required) in TABLE_SPECS.items():
                if table not in tables:
                    continue
                columns = _columns(db, table)
                if not required <= columns:
                    counts[table] = {"available": False, "missing_columns": sorted(required - columns)}
                    continue
                optional = sorted(columns & {
                    "correlationId", "globalTid", "deviceId", "contextId",
                    "streamId", "graphId", "channelID", "gridX", "gridY",
                    "gridZ", "blockX", "blockY", "blockZ", "bytes",
                    "copyKind", "srcKind", "dstKind", "syncType",
                } - required)
                selected = sorted(required) + optional
                query = f'SELECT {", ".join(chr(34)+name+chr(34) for name in selected)} FROM "{table}"'
                table_count = 0
                for raw in db.execute(query):
                    row = dict(zip(selected, raw))
                    start, end = int(row["start"]), int(row["end"])
                    name = None
                    if table == "CUPTI_ACTIVITY_KIND_RUNTIME":
                        name = strings.get(int(row["nameId"]), f"nameId:{row['nameId']}")
                        kind = classify_runtime(name)
                    elif table == "CUPTI_ACTIVITY_KIND_KERNEL":
                        name = strings.get(int(row["shortName"]), f"shortName:{row['shortName']}")
                        kind = "kernel"
                    elif table == "CUPTI_ACTIVITY_KIND_MEMCPY":
                        name = "cuda_memcpy"
                        kind = "transfer"
                        row["copy_kind_name"] = MEMCPY_KIND.get(int(row["copyKind"]), f"UNKNOWN_{row['copyKind']}")
                        row["src_memory_name"] = MEMORY_KIND.get(int(row["srcKind"]), f"UNKNOWN_{row['srcKind']}")
                        row["dst_memory_name"] = MEMORY_KIND.get(int(row["dstKind"]), f"UNKNOWN_{row['dstKind']}")
                    else:
                        name = "cuda_synchronization"
                        kind = "sync"
                    global_tid = row.get("globalTid")
                    event = {
                        "schema_version": "1.0",
                        "run_id": resolved_run_id,
                        "request_id": None,
                        "event_id": str(uuid.uuid4()),
                        "kind": kind,
                        "name": name,
                        "source": "nsys_sqlite",
                        "source_table": table,
                        "source_clock": "nsys_activity_ns",
                        "source_start_ns": start,
                        "source_end_ns": end,
                        "duration_ns": max(0, end - start),
                        "monotonic_ns": None,
                        "wall_time": None,
                        "correlation_id": row.get("correlationId"),
                        "global_tid": global_tid,
                        "thread_name": strings.get(int(row["nameId"])) if "nameId" in row and row["nameId"] is not None else None,
                        "process": runtime_process(int(global_tid), processes) if global_tid is not None else None,
                        "device_id": row.get("deviceId"),
                        "context_id": row.get("contextId"),
                        "stream_id": row.get("streamId"),
                        "payload": row,
                    }
                    output.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                    imported += 1
                    table_count += 1
                    by_kind[kind] = by_kind.get(kind, 0) + 1
                counts[table] = {"available": True, "imported": table_count}
    report = {
        "schema_version": "1.0",
        "run_id": resolved_run_id,
        "source_database": str(database),
        "source_sha256": sha256_file(database),
        "source_clock": "nsys_activity_ns",
        "host_clock_correlation": "not inferred; Nsight activity timestamps are preserved in a separate clock domain",
        "tables": counts,
        "imported_event_count": imported,
        "events_by_kind": by_kind,
        "events_file": str(events_path.relative_to(run_dir)),
        "read_only_source": True,
        "limitations": [
            "Nsight activity timestamps are not converted to host monotonic_ns without an explicit clock-correlation marker.",
            "Request IDs are not inferred from CUDA correlation IDs; an engine/runner correlation adapter is required.",
            "Missing activity tables or columns are reported unavailable, not as zero activity.",
            "The source SQLite database is opened read-only and is never modified.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    collection_path = run_dir / "collection_report.json"
    if collection_path.is_file():
        collection = json.loads(collection_path.read_text(encoding="utf-8"))
        collection["nsys_imported_event_count"] = imported
        collection.setdefault("coverage", {})["nsys_profile_import"] = True
        collection["coverage"]["nsys_activity_events"] = imported > 0
        collection_path.write_text(json.dumps(collection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sums = []
    for item in sorted(run_dir.rglob("*")):
        if item.is_file() and item.name != "SHA256SUMS":
            sums.append(f"{sha256_file(item)}  {item.relative_to(run_dir)}")
    (run_dir / "SHA256SUMS").write_text("\n".join(sums) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=pathlib.Path)
    parser.add_argument("--run-dir", required=True, type=pathlib.Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    report = import_database(args.database, args.run_dir, args.run_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
