#!/usr/bin/env python3
"""Import NEPENTHES JSONL and Nsight Systems SQLite into a normalized LEONES DB.

The importer preserves source rows and provenance. Nsight timestamps are kept in
their original nanosecond clock domain; no cross-clock or request/kernel join is
fabricated. JSONL and Nsight artifacts are hashed before ingestion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any

NSYS_TABLES = {
    "CUPTI_ACTIVITY_KIND_KERNEL": "cuda_kernel",
    "CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL": "cuda_kernel",
    "CUPTI_ACTIVITY_KIND_MEMCPY": "cuda_memcpy",
    "CUPTI_ACTIVITY_KIND_MEMCPY2": "cuda_memcpy",
    "CUPTI_ACTIVITY_KIND_MEMSET": "cuda_memset",
    "CUPTI_ACTIVITY_KIND_RUNTIME": "cuda_runtime",
    "CUPTI_ACTIVITY_KIND_DRIVER": "cuda_driver",
    "CUPTI_ACTIVITY_KIND_GRAPH_TRACE": "cuda_graph_trace",
    "CUPTI_ACTIVITY_KIND_SYNCHRONIZATION": "cuda_synchronization",
    "CUPTI_ACTIVITY_KIND_CUDA_EVENT": "cuda_event",
    "CUPTI_ACTIVITY_KIND_OVERHEAD": "cuda_overhead",
}
JSONL_REQUIRED = {
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "monotonic_ns", "request_id", "event_kind", "label", "value0", "value1",
    "duration_ns", "flags",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def table_names(db: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.hex()
    return value


def sqlite_int64(value: int, *, field: str) -> int:
    """Encode uint64 values in SQLite's signed INTEGER domain.

    Values above INT64_MAX are stored using two's-complement representation.
    The original unsigned value remains preserved in the event raw_json.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    if -(1 << 63) <= value <= (1 << 63) - 1:
        return value
    if 0 <= value <= (1 << 64) - 1:
        return value - (1 << 64)
    raise ValueError(f"{field} is outside the supported int64/uint64 range: {value}")


def load_string_ids(db: sqlite3.Connection, names: set[str]) -> dict[int, str]:
    for table in ("StringIds", "StringId", "StringTable"):
        if table not in names:
            continue
        cols = columns(db, table)
        id_col = next((c for c in ("id", "stringId", "string_id") if c in cols), None)
        value_col = next((c for c in ("value", "name", "string") if c in cols), None)
        if id_col and value_col:
            return {
                int(row[0]): str(row[1])
                for row in db.execute(
                    f'SELECT "{id_col}", "{value_col}" FROM "{table}"'
                )
            }
    return {}


def inspect_nsys(path: Path) -> dict:
    """Report Nsight SQLite schema without importing or exposing row payloads."""
    if not path.is_file():
        raise ValueError(f"Nsight SQLite file does not exist: {path}")
    db = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        names = table_names(db)
        tables = []
        for table in sorted(names):
            mapped = NSYS_TABLES.get(table)
            if not mapped and not table.lower().startswith("cupti_activity_kind_"):
                continue
            quoted = table.replace('"', '""')
            count = int(db.execute(f'SELECT COUNT(*) FROM "{quoted}"').fetchone()[0])
            cols = [row[1] for row in db.execute(f'PRAGMA table_info("{quoted}")')]
            tables.append({
                "table": table,
                "mapped_kind": mapped,
                "row_count": count,
                "columns": cols,
            })
        string_tables = []
        for table in ("StringIds", "StringId", "StringTable"):
            if table in names:
                string_tables.append({
                    "table": table,
                    "columns": sorted(columns(db, table)),
                    "row_count": int(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]),
                })
        return {
            "file": str(path.resolve()),
            "size_bytes": path.stat().st_size,
            "recognized_activity_tables": [x for x in tables if x["mapped_kind"]],
            "other_cupti_activity_tables": [x for x in tables if not x["mapped_kind"]],
            "string_tables": string_tables,
            "policy": "schema metadata only; no source rows or cross-clock correlation are emitted",
        }
    finally:
        db.close()


def first(row: dict[str, Any], candidates: tuple[str, ...]) -> Any:
    for key in candidates:
        if key in row and row[key] is not None:
            return row[key]
    return None


def event_rows(path: Path):
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL line {line_no}: invalid JSON: {exc}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"JSONL line {line_no}: event must be an object")
            missing = JSONL_REQUIRED - item.keys()
            if missing:
                raise ValueError(
                    f"JSONL line {line_no}: missing fields: {', '.join(sorted(missing))}"
                )
            if item["schema_version"] != "1.0":
                raise ValueError(f"JSONL line {line_no}: unsupported schema_version")
            for field in ("run_id", "event_id", "source", "event_kind", "label"):
                if not isinstance(item[field], str) or not item[field]:
                    raise ValueError(f"JSONL line {line_no}: {field} must be a non-empty string")
            if item["event_id"] in seen:
                raise ValueError(f"JSONL line {line_no}: duplicate event_id {item['event_id']}")
            seen.add(item["event_id"])
            for field in ("timestamp_unix_ns", "monotonic_ns", "request_id",
                          "value0", "value1", "duration_ns", "flags"):
                if isinstance(item[field], bool) or not isinstance(item[field], int):
                    raise ValueError(f"JSONL line {line_no}: {field} must be an integer")
            counts[str(item["event_kind"])] += 1
            yield item
    if not seen:
        raise ValueError("JSONL contains no events")
    return counts


def init_output(db: sqlite3.Connection) -> None:
    migration_dir = Path(__file__).resolve().parents[1] / "db" / "migrations"
    for version in ("002_nepenthes_observability.sql", "003_nepenthes_nsys_only.sql"):
        migration = migration_dir / version
        if migration.is_file():
            db.executescript(migration.read_text(encoding="utf-8"))


def import_all(jsonl: Path, nsys: Path, output: Path, import_id: str) -> dict:
    if not jsonl.is_file() or not nsys.is_file():
        raise ValueError("both JSONL and Nsight SQLite input files must exist")
    resolved_output = output.resolve()
    if resolved_output in {jsonl.resolve(), nsys.resolve()}:
        raise ValueError("output database must not overwrite either source artifact")
    output.parent.mkdir(parents=True, exist_ok=True)
    events = list(event_rows(jsonl))
    event_counts = Counter(str(e["event_kind"]) for e in events)
    source = sqlite3.connect(f"file:{nsys.resolve()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    names = table_names(source)
    strings = load_string_ids(source, names)
    activities: list[tuple] = []
    activity_counts: Counter[str] = Counter()
    activity_id = 0

    for table, kind in NSYS_TABLES.items():
        if table not in names:
            continue
        for source_row in source.execute(f'SELECT * FROM "{table}"'):
            row = {k: json_value(source_row[k]) for k in source_row.keys()}
            start = first(row, ("start", "startNs", "start_ns", "begin", "timestamp"))
            end = first(row, ("end", "endNs", "end_ns", "finish"))
            duration = (
                int(end) - int(start)
                if isinstance(start, (int, float)) and isinstance(end, (int, float))
                else None
            )
            raw_name = first(row, ("name", "demangledName", "shortName", "nameId"))
            name = strings.get(int(raw_name), str(raw_name)) if isinstance(raw_name, (int, float)) else raw_name
            if name is None:
                name = first(row, ("eventClass", "syncType", "overheadType"))
            activity_id += 1
            activities.append((
                import_id, activity_id, table, kind,
                start, end, duration,
                first(row, ("correlationId", "correlation_id")),
                first(row, ("globalPid", "global_pid")),
                first(row, ("processId", "pid")),
                first(row, ("deviceId", "device_id")),
                first(row, ("contextId", "context_id")),
                first(row, ("streamId", "stream_id")),
                str(name) if name is not None else None,
                json.dumps(row, ensure_ascii=False, sort_keys=True),
            ))
            activity_counts[kind] += 1
    source.close()

    run_ids = sorted({str(e["run_id"]) for e in events})
    if len(run_ids) != 1:
        raise ValueError(f"JSONL must contain exactly one run_id; found {run_ids}")
    if not activities:
        raise ValueError("Nsight SQLite contains no recognized CUDA activity rows")

    out = sqlite3.connect(output)
    try:
        init_output(out)
        with out:
            out.execute(
                """INSERT INTO nepenthes_imports
                (import_id,run_id,jsonl_path,jsonl_sha256,nsys_path,nsys_sha256,
                 event_count,activity_count,event_kinds_json,activity_kinds_json,correlation_policy)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (import_id, run_ids[0], str(jsonl.resolve()), sha256(jsonl),
                 str(nsys.resolve()), sha256(nsys), len(events), len(activities),
                 json.dumps(dict(event_counts), sort_keys=True),
                 json.dumps(dict(activity_counts), sort_keys=True),
                 "No automatic JSONL-to-Nsight join: monotonic and Nsight clocks are not calibrated; request_id is not a CUPTI correlation_id."),
            )
            out.executemany(
                """INSERT INTO nepenthes_events
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(import_id, e["event_id"], e["run_id"], e["source"],
                  e["schema_version"], e["timestamp_unix_ns"], e["monotonic_ns"],
                  e["request_id"], e["event_kind"], e["label"],
                  sqlite_int64(e["value0"], field="value0"),
                  sqlite_int64(e["value1"], field="value1"),
                  e["duration_ns"], e["flags"],
                  json.dumps(e, ensure_ascii=False, sort_keys=True)) for e in events],
            )
            out.executemany(
                """INSERT INTO nsys_activities
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", activities
            )
    finally:
        out.close()

    return {
        "import_id": import_id, "run_id": run_ids[0],
        "event_count": len(events), "event_kinds": dict(event_counts),
        "activity_count": len(activities), "activity_kinds": dict(activity_counts),
        "recognized_nsys_tables": sorted(t for t in NSYS_TABLES if t in names),
        "output": str(output.resolve()),
        "correlation": "not joined; clock domains and IDs are not interchangeable",
    }



def import_nsys_only(nsys: Path, output: Path, import_id: str) -> dict:
    """Import a standalone Nsight export without fabricating a paired JSONL run."""
    if not nsys.is_file():
        raise ValueError(f"Nsight SQLite file does not exist: {nsys}")
    resolved_output = output.resolve()
    if resolved_output == nsys.resolve():
        raise ValueError("output database must not overwrite the Nsight source artifact")
    output.parent.mkdir(parents=True, exist_ok=True)

    source = sqlite3.connect(f"file:{nsys.resolve()}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row
    try:
        names = table_names(source)
        strings = load_string_ids(source, names)
        detected: dict[str, int] = {}
        for table in sorted(names):
            if table.lower().startswith("cupti_activity_kind_"):
                quoted = table.replace('"', '""')
                detected[table] = int(source.execute(
                    f'SELECT COUNT(*) FROM "{quoted}"'
                ).fetchone()[0])

        activities: list[tuple] = []
        activity_counts: Counter[str] = Counter()
        activity_id = 0
        for table, kind in NSYS_TABLES.items():
            if table not in names:
                continue
            for source_row in source.execute(f'SELECT * FROM "{table}"'):
                row = {k: json_value(source_row[k]) for k in source_row.keys()}
                start = first(row, ("start", "startNs", "start_ns", "begin", "timestamp"))
                end = first(row, ("end", "endNs", "end_ns", "finish"))
                duration = (
                    int(end) - int(start)
                    if isinstance(start, (int, float)) and isinstance(end, (int, float))
                    else None
                )
                raw_name = first(row, ("name", "demangledName", "shortName", "nameId"))
                if isinstance(raw_name, (int, float)):
                    name = strings.get(int(raw_name), str(raw_name))
                else:
                    name = raw_name
                if name is None:
                    name = first(row, ("eventClass", "syncType", "overheadType"))
                activity_id += 1
                activities.append((
                    import_id, activity_id, table, kind,
                    start, end, duration,
                    first(row, ("correlationId", "correlation_id")),
                    first(row, ("globalPid", "global_pid")),
                    first(row, ("processId", "pid")),
                    first(row, ("deviceId", "device_id")),
                    first(row, ("contextId", "context_id")),
                    first(row, ("streamId", "stream_id")),
                    str(name) if name is not None else None,
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                ))
                activity_counts[kind] += 1
    finally:
        source.close()

    if not activities:
        raise ValueError("Nsight SQLite contains no supported CUPTI activity rows")
    unsupported = {table: count for table, count in detected.items() if table not in NSYS_TABLES and count > 0}
    coverage = {
        "supported_tables": sorted(table for table in detected if table in NSYS_TABLES),
        "unsupported_tables": sorted(unsupported),
        "unsupported_row_count": sum(unsupported.values()),
        "detected_cupti_tables": len(detected),
        "imported_activity_rows": len(activities),
        "status": "partial" if unsupported else "complete_for_detected_cupti_tables",
    }

    out = sqlite3.connect(output)
    try:
        init_output(out)
        with out:
            out.execute(
                """INSERT INTO nepenthes_nsys_imports
                (import_id,nsys_path,nsys_sha256,activity_count,activity_kinds_json,
                 detected_table_counts_json,coverage_json,provenance,correlation_policy)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (import_id, str(nsys.resolve()), sha256(nsys), len(activities),
                 json.dumps(dict(activity_counts), sort_keys=True),
                 json.dumps(detected, sort_keys=True), json.dumps(coverage, sort_keys=True),
                 "standalone_nsys_capture_without_paired_nepenthes_jsonl",
                 "No NEPENTHES run_id or request correlation asserted; Nsight timestamps and CUPTI correlation IDs remain within the Nsight source domain."),
            )
            out.executemany(
                """INSERT INTO nepenthes_nsys_activities
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", activities
            )
    finally:
        out.close()

    return {
        "import_id": import_id,
        "mode": "nsys_only",
        "jsonl": None,
        "run_id": None,
        "nsys_path": str(nsys.resolve()),
        "nsys_sha256": sha256(nsys),
        "activity_count": len(activities),
        "activity_kinds": dict(activity_counts),
        "detected_table_counts": detected,
        "coverage": coverage,
        "output": str(output.resolve()),
        "correlation": "none; standalone Nsight provenance, no paired NEPENTHES run is claimed",
    }



def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-nsys", type=Path, help="inspect Nsight SQLite schema without importing")
    mode.add_argument("--jsonl", type=Path, help="NEPENTHES JSONL input for paired import")
    mode.add_argument("--nsys-only", type=Path, help="import a standalone Nsight SQLite without paired JSONL")
    parser.add_argument("--nsys-sqlite", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--import-id", default=None)
    args = parser.parse_args()
    try:
        if args.inspect_nsys is not None:
            if args.nsys_sqlite is not None or args.output is not None:
                parser.error("--inspect-nsys cannot be combined with --nsys-sqlite/--output")
            result = inspect_nsys(args.inspect_nsys)
        elif args.nsys_only is not None:
            if args.nsys_sqlite is not None:
                parser.error("--nsys-only cannot be combined with --nsys-sqlite")
            if args.output is None:
                parser.error("--nsys-only requires --output")
            import_id = args.import_id or f"nsys-{sha256(args.nsys_only)[:12]}"
            result = import_nsys_only(args.nsys_only, args.output, import_id)
        else:
            if args.nsys_sqlite is None or args.output is None:
                parser.error("--jsonl requires --nsys-sqlite and --output")
            import_id = args.import_id or f"nepenthes-{sha256(args.jsonl)[:12]}"
            result = import_all(args.jsonl, args.nsys_sqlite, args.output, import_id)
    except (OSError, sqlite3.Error, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
