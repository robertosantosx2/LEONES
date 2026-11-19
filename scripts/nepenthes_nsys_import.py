#!/usr/bin/env python3
"""Import NEPENTHES JSONL and Nsight Systems SQLite into a normalized LEONES DB.

The importer preserves source rows, provenance, and explicit NVTX request markers. Nsight timestamps are kept in
their original nanosecond clock domain; no cross-clock or request/kernel join is
fabricated. JSONL and Nsight artifacts are hashed before ingestion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
    "NVTX_EVENTS": "nvtx_event",
}
JSONL_REQUIRED = {
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "monotonic_ns", "request_id", "event_kind", "label", "value0", "value1",
    "duration_ns", "flags",
}
JSONL_V11_REQUIRED = {
    "correlation_token", "attribution_level", "backend", "memory_kind",
    "memcpy_kind", "raw_memcpy_kind", "sync_type", "kv_op", "clock_domain",
}
JSONL_V11_ENUMS = {
    "attribution_level": {"exact", "windowed", "device_wide", "estimated"},
    "backend": {"cpu", "cuda", "metal", "vulkan", "rocm", "musa"},
    "memory_kind": {"host", "host_pinned", "device", "managed", "vmm"},
    "memcpy_kind": {"host_to_host", "host_to_device", "device_to_host",
                    "device_to_device", "peer_to_peer", "default"},
    "sync_type": {"stream", "device", "event", "context"},
    "kv_op": {"clear", "seq_rm", "seq_cp", "seq_keep", "seq_add", "seq_div",
              "prepare", "update", "apply_ubatch"},
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


def sqlite_numeric(value: Any, *, field: str) -> Any:
    """Encode uint64 integers for SQLite while preserving source JSON separately."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field} must not be boolean")
    if isinstance(value, int):
        return sqlite_int64(value, field=field)
    if isinstance(value, float):
        return value
    raise ValueError(f"{field} must be an integer, float, or null")


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



def load_enum_tables(db: sqlite3.Connection, names: set[str]) -> tuple[dict[str, dict[int, str]], dict[str, Any]]:
    """Load enum labels from the Nsight SQLite itself; never hard-code enum numbers."""
    mappings: dict[str, dict[int, str]] = {}
    metadata: dict[str, Any] = {}
    value_candidates = ("id", "value", "enumvalue", "enum_value", "key", "valueid",
                        "value_id", "code", "ordinal")
    label_candidates = ("name", "label", "description", "string", "enumname",
                        "enum_name", "valuename", "value_name", "text")
    for table in sorted(name for name in names if name.upper().startswith("ENUM_CUDA_")):
        cols = sorted(columns(db, table))
        quoted = table.replace('"', '""')
        cursor = db.execute(f'SELECT * FROM "{quoted}"')
        row_columns = [item[0] for item in cursor.description]
        rows = [dict(zip(row_columns, row)) for row in cursor]
        lower = {column.lower(): column for column in cols}
        value_col = next((lower[name] for name in value_candidates if name in lower), None)
        label_col = next((lower[name] for name in label_candidates if name in lower), None)
        if value_col is None or label_col is None or value_col == label_col:
            numeric_cols = [column for column in cols
                            if any(isinstance(row.get(column), int) and not isinstance(row.get(column), bool)
                                   for row in rows)]
            text_cols = [column for column in cols
                         if any(isinstance(row.get(column), str) for row in rows)]
            value_col = value_col or (numeric_cols[0] if numeric_cols else None)
            label_col = label_col or next((column for column in text_cols if column != value_col), None)
        mapping: dict[int, str] = {}
        if value_col and label_col:
            for row in rows:
                value = row.get(value_col)
                label = row.get(label_col)
                if isinstance(value, int) and not isinstance(value, bool) and isinstance(label, str):
                    mapping[value] = label
        mappings[table.upper()] = mapping
        metadata[table] = {
            "columns": cols,
            "row_count": len(rows),
            "value_column": value_col,
            "label_column": label_col,
            "mapping": {str(key): value for key, value in sorted(mapping.items())},
            "status": "decoded" if mapping else "unmapped_schema",
        }
    return mappings, metadata


def decode_activity_enums(row: dict[str, Any], enum_maps: dict[str, dict[int, str]]) -> dict[str, Any]:
    """Decode memcpy operation and source/destination memory kinds using captured enum tables."""
    fields = {
        "copy_kind": (("copyKind", "copy_kind", "memcpyKind", "memcpy_kind", "operation"),
                      "ENUM_CUDA_MEMCPY_OPER"),
        "src_kind": (("srcKind", "src_kind", "sourceKind", "source_kind"),
                     "ENUM_CUDA_MEM_KIND"),
        "dst_kind": (("dstKind", "dst_kind", "destinationKind", "destination_kind"),
                     "ENUM_CUDA_MEM_KIND"),
    }
    decoded: dict[str, Any] = {}
    for output_name, (candidates, table) in fields.items():
        value = first(row, candidates)
        label = None
        if isinstance(value, int) and not isinstance(value, bool):
            label = enum_maps.get(table, {}).get(value)
        decoded[output_name] = {
            "value": value,
            "label": label,
            "enum_table": table,
        }
    relevant = [item for item in decoded.values() if item["value"] is not None]
    if not relevant:
        status = "not_applicable"
    elif all(item["label"] is not None for item in relevant):
        status = "decoded"
    elif any(item["label"] is not None for item in relevant):
        status = "partial"
    else:
        status = "unknown_value_or_missing_enum_table"
    return {
        "copy_kind_value": decoded["copy_kind"]["value"],
        "copy_kind_name": decoded["copy_kind"]["label"],
        "src_kind_value": decoded["src_kind"]["value"],
        "src_kind_name": decoded["src_kind"]["label"],
        "dst_kind_value": decoded["dst_kind"]["value"],
        "dst_kind_name": decoded["dst_kind"]["label"],
        "enum_decode_status": status,
        "raw": decoded,
    }


def ensure_enum_schema(db: sqlite3.Connection) -> None:
    """Idempotently add queryable enum columns to both paired and Nsight-only stores."""
    additions = {
        "nepenthes_imports": [("enum_tables_json", "TEXT NOT NULL DEFAULT '{}'"),
                              ("nsys_clock_calibration_json", "TEXT NOT NULL DEFAULT '{}'")],
        "nepenthes_nsys_imports": [("enum_tables_json", "TEXT NOT NULL DEFAULT '{}'"),
                                  ("nsys_clock_calibration_json", "TEXT NOT NULL DEFAULT '{}'")],
        "nepenthes_events": [
            ("correlation_token", "INTEGER"), ("attribution_level", "TEXT"),
            ("backend", "TEXT"), ("memory_kind", "TEXT"), ("memcpy_kind", "TEXT"),
            ("raw_memcpy_kind", "INTEGER"), ("sync_type", "TEXT"), ("kv_op", "TEXT"),
        ],
        "nsys_activities": [
            ("copy_kind_value", "INTEGER"), ("copy_kind_name", "TEXT"),
            ("src_kind_value", "INTEGER"), ("src_kind_name", "TEXT"),
            ("dst_kind_value", "INTEGER"), ("dst_kind_name", "TEXT"),
            ("enum_decode_status", "TEXT NOT NULL DEFAULT 'not_applicable'"),
            ("nvtx_correlation_token", "INTEGER"), ("nvtx_marker_phase", "TEXT"),
            ("nvtx_marker_request_id", "INTEGER"), ("attributed_request_token", "INTEGER"),
            ("attribution_level", "TEXT"), ("attribution_status", "TEXT NOT NULL DEFAULT 'unattributed'"),
        ],
        "nepenthes_nsys_activities": [
            ("copy_kind_value", "INTEGER"), ("copy_kind_name", "TEXT"),
            ("src_kind_value", "INTEGER"), ("src_kind_name", "TEXT"),
            ("dst_kind_value", "INTEGER"), ("dst_kind_name", "TEXT"),
            ("enum_decode_status", "TEXT NOT NULL DEFAULT 'not_applicable'"),
            ("nvtx_correlation_token", "INTEGER"), ("nvtx_marker_phase", "TEXT"),
            ("nvtx_marker_request_id", "INTEGER"), ("attributed_request_token", "INTEGER"),
            ("attribution_level", "TEXT"), ("attribution_status", "TEXT NOT NULL DEFAULT 'unattributed'"),
        ],
    }
    for table, definitions in additions.items():
        if table not in table_names(db):
            continue
        existing = columns(db, table)
        for name, definition in definitions:
            if name not in existing:
                db.execute(f'ALTER TABLE "{table}" ADD COLUMN "{name}" {definition}')
    db.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES ('004_nepenthes_enum_decoding')")
    db.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES ('005_nepenthes_nvtx_correlation')")
    db.execute("INSERT OR IGNORE INTO schema_migrations(version) VALUES ('006_nepenthes_typed_event_metadata')")
    if "nsys_activities" in table_names(db):
        db.execute("CREATE INDEX IF NOT EXISTS idx_nsys_activities_attributed_request ON nsys_activities(import_id,attributed_request_token,attribution_level)")
    if "nepenthes_nsys_activities" in table_names(db):
        db.execute("CREATE INDEX IF NOT EXISTS idx_nsys_only_activities_attributed_request ON nepenthes_nsys_activities(import_id,attributed_request_token,attribution_level)")


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
        _, enum_metadata = load_enum_tables(db, names)
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
            "enum_tables": enum_metadata,
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
            if item["schema_version"] not in ("1.0", "1.1"):
                raise ValueError(f"JSONL line {line_no}: unsupported schema_version")
            if item["schema_version"] == "1.1":
                missing_typed = JSONL_V11_REQUIRED - item.keys()
                if missing_typed:
                    raise ValueError(
                        f"JSONL line {line_no}: missing typed metadata fields: {', '.join(sorted(missing_typed))}"
                    )
                for field, allowed in JSONL_V11_ENUMS.items():
                    value = item[field]
                    if value is not None and (not isinstance(value, str) or value not in allowed):
                        raise ValueError(f"JSONL line {line_no}: invalid {field}: {value!r}")
                token = item["correlation_token"]
                if token is not None and (isinstance(token, bool) or not isinstance(token, int) or token <= 0):
                    raise ValueError(f"JSONL line {line_no}: correlation_token must be a positive integer or null")
                raw_kind = item["raw_memcpy_kind"]
                if raw_kind is not None and (isinstance(raw_kind, bool) or not isinstance(raw_kind, int) or raw_kind < 0):
                    raise ValueError(f"JSONL line {line_no}: raw_memcpy_kind must be a non-negative integer or null")
                if raw_kind is not None and item["memcpy_kind"] is None:
                    raise ValueError(f"JSONL line {line_no}: raw_memcpy_kind requires memcpy_kind")
                if token is not None and item["attribution_level"] != "exact":
                    raise ValueError(f"JSONL line {line_no}: token-bearing events must have exact attribution")
                if item["clock_domain"] != "steady_clock":
                    raise ValueError(f"JSONL line {line_no}: unsupported clock_domain")
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



NVTX_MARKER_RE = re.compile(
    r"nepenthes\.(request|batch)\.(start|end)\s+token=(\d+)(?:\s+request=(\d+))?"
)


def parse_nvtx_marker(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, str):
        return None
    match = NVTX_MARKER_RE.search(message)
    if not match:
        return None
    scope, phase, token_text, request_text = match.groups()
    request_id = int(request_text) if request_text is not None else None
    if scope == "request" and request_id is None:
        return None
    if scope == "batch" and request_id is not None:
        return None
    return {
        "scope": scope,
        "phase": phase,
        "token": int(token_text),
        "request_id": request_id,
        "message": message,
    }


def collect_nsys_nvtx_markers(db: sqlite3.Connection, names: set[str],
                              strings: dict[int, str]) -> list[dict[str, Any]]:
    if "NVTX_EVENTS" not in names:
        return []
    markers: list[dict[str, Any]] = []
    for source_row in db.execute('SELECT * FROM "NVTX_EVENTS"'):
        row = {key: json_value(source_row[key]) for key in source_row.keys()}
        message = first(row, ("text", "message", "name", "textId", "messageId", "nameId"))
        if isinstance(message, (int, float)):
            message = strings.get(int(message), str(message))
        parsed = parse_nvtx_marker(message)
        if parsed is None:
            continue
        start = first(row, ("start", "startNs", "start_ns", "timestamp"))
        if not isinstance(start, (int, float)):
            continue
        parsed["start_ns"] = int(start)
        parsed["end_ns"] = int(first(row, ("end", "endNs", "end_ns")) or start)
        process_id = first(row, ("globalPid", "global_pid", "processId", "pid"))
        parsed["process_id"] = process_id if isinstance(process_id, int) and not isinstance(process_id, bool) else None
        markers.append(parsed)
    return markers


def host_nvtx_markers(events: list[dict[str, Any]]) -> dict[tuple[str, int, str], list[dict[str, int]]]:
    result: dict[tuple[str, int, str], list[dict[str, int]]] = {}
    for event in events:
        if event.get("event_kind") != "nvtx_marker":
            continue
        token = event.get("correlation_token")
        label = event.get("label")
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            continue
        if label in ("request.start", "request.end"):
            scope = "request"
            if isinstance(event.get("request_id"), bool) or not isinstance(event.get("request_id"), int) or event["request_id"] <= 0:
                continue
        elif label in ("batch.start", "batch.end"):
            scope = "batch"
            if event.get("request_id", 0) not in (0, None):
                continue
        else:
            continue
        before = event.get("value0")
        after = event.get("value1")
        if not isinstance(before, int) or not isinstance(after, int) or after < before:
            continue
        phase = "start" if label.endswith(".start") else "end"
        key = (scope, token, phase)
        result.setdefault(key, []).append({
            "host_mid_ns": (before + after) // 2,
            "bracket_ns": after - before,
            "timestamp_unix_ns": int(event.get("timestamp_unix_ns") or 0),
        })
    return result


def calibrate_host_to_nsys(
    host_markers: dict[tuple[str, int, str], list[dict[str, int]]],
    nsys_markers: list[dict[str, Any]],
) -> dict[str, Any]:
    nsys_by_key: dict[tuple[str, int, str], list[int]] = {}
    for marker in nsys_markers:
        nsys_by_key.setdefault(
            (marker["scope"], marker["token"], marker["phase"]), []
        ).append(marker["start_ns"])
    pairs = []
    for key, host_values in host_markers.items():
        nsys_values = nsys_by_key.get(key, [])
        if len(host_values) == 1 and len(nsys_values) == 1:
            host = host_values[0]
            pairs.append({
                "scope": key[0], "token": key[1], "phase": key[2],
                "host_monotonic_ns": host["host_mid_ns"],
                "nsys_timestamp_ns": nsys_values[0],
                "offset_ns": nsys_values[0] - host["host_mid_ns"],
                "host_bracket_ns": host["bracket_ns"],
            })
    pairs.sort(key=lambda item: item["host_monotonic_ns"])
    result: dict[str, Any] = {
        "matched_marker_pairs": len(pairs),
        "nsight_clock_calibrated": False,
        "offset_start_ns": None,
        "offset_end_ns": None,
        "drift_ns": None,
        "drift_ppm": None,
        "host_bracket_uncertainty_ns": None,
        "pairs": pairs,
    }
    if pairs:
        result["offset_start_ns"] = pairs[0]["offset_ns"]
        result["offset_end_ns"] = pairs[-1]["offset_ns"]
        result["host_bracket_uncertainty_ns"] = max(
            (item["host_bracket_ns"] + 1) // 2 for item in pairs
        )
    if len(pairs) >= 2:
        span = pairs[-1]["host_monotonic_ns"] - pairs[0]["host_monotonic_ns"]
        if span > 0:
            drift = pairs[-1]["offset_ns"] - pairs[0]["offset_ns"]
            result["drift_ns"] = drift
            result["drift_ppm"] = (drift / span) * 1_000_000
            result["nsight_clock_calibrated"] = True
    return result


def build_nvtx_token_windows(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # Windows are process- and scope-scoped. Request and batch tokens may have
    # equal numeric values without colliding; overlap is resolved per scope.
    grouped: dict[tuple[int, str, int], dict[str, list[int]]] = {}
    for marker in markers:
        process_id = marker.get("process_id")
        scope = marker.get("scope")
        token = marker.get("token")
        if isinstance(process_id, bool) or not isinstance(process_id, int):
            continue
        if scope not in ("request", "batch"):
            continue
        if isinstance(token, bool) or not isinstance(token, int) or token <= 0:
            continue
        grouped.setdefault((process_id, scope, token), {"start": [], "end": []})[marker["phase"]].append(
            marker["start_ns"]
        )
    windows = []
    for (process_id, scope, token), phases in grouped.items():
        if len(phases["start"]) == 1 and len(phases["end"]) == 1:
            start_ns, end_ns = phases["start"][0], phases["end"][0]
            if end_ns > start_ns:
                windows.append({
                    "process_id": process_id, "scope": scope, "token": token,
                    "start_ns": start_ns, "end_ns": end_ns,
                })
    return sorted(windows, key=lambda item: (item["process_id"], item["scope"], item["start_ns"]))


def build_nvtx_request_windows(markers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Backward-compatible alias; returned windows may have request or batch scope."""
    return build_nvtx_token_windows(markers)


def attribute_nsys_activity(
    start_ns: Any, end_ns: Any, windows: list[dict[str, Any]], process_id: Any,
) -> tuple[int | None, str | None, str, int | None, str | None, str]:
    if not isinstance(start_ns, (int, float)) or not isinstance(end_ns, (int, float)):
        return None, None, "missing_activity_timestamps", None, None, "missing_activity_timestamps"
    if isinstance(process_id, bool) or not isinstance(process_id, int):
        return None, None, "missing_activity_process_identity", None, None, "missing_activity_process_identity"

    def match_scope(scope: str) -> tuple[int | None, str | None, str]:
        process_windows = [
            window for window in windows
            if window["process_id"] == process_id and window["scope"] == scope
        ]
        if not process_windows:
            return None, None, f"missing_process_{scope}_window"
        matches = [
            window["token"] for window in process_windows
            if window["start_ns"] <= int(start_ns) and int(end_ns) <= window["end_ns"]
        ]
        if len(matches) == 1:
            return matches[0], "windowed", f"unique_explicit_{scope}_window"
        if len(matches) > 1:
            return None, None, f"overlapping_{scope}_windows"
        return None, None, f"outside_{scope}_window"

    request_token, request_level, request_status = match_scope("request")
    batch_token, batch_level, batch_status = match_scope("batch")
    return request_token, request_level, request_status, batch_token, batch_level, batch_status


def init_output(db: sqlite3.Connection) -> None:
    migration_dir = Path(__file__).resolve().parents[1] / "db" / "migrations"
    for version in ("002_nepenthes_observability.sql", "003_nepenthes_nsys_only.sql", "006_nepenthes_typed_event_metadata.sql"):
        migration = migration_dir / version
        if not migration.is_file():
            continue
        if version == "006_nepenthes_typed_event_metadata.sql":
            applied = db.execute(
                "SELECT 1 FROM schema_migrations WHERE version = ?",
                ("006_nepenthes_typed_event_metadata",),
            ).fetchone()
            if applied:
                continue
        db.executescript(migration.read_text(encoding="utf-8"))
    ensure_enum_schema(db)


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
    enum_maps, enum_metadata = load_enum_tables(source, names)
    nsys_markers = collect_nsys_nvtx_markers(source, names, strings)
    host_markers = host_nvtx_markers(events)
    nsys_clock_calibration = calibrate_host_to_nsys(host_markers, nsys_markers)
    nvtx_windows = build_nvtx_token_windows(nsys_markers)
    activities: list[tuple] = []
    activity_counts: Counter[str] = Counter()
    activity_id = 0

    for table, kind in NSYS_TABLES.items():
        if table not in names:
            continue
        for source_row in source.execute(f'SELECT * FROM "{table}"'):
            row = {k: json_value(source_row[k]) for k in source_row.keys()}
            enum_decoding = decode_activity_enums(row, enum_maps)
            row["_nepenthes_enum_decoding"] = enum_decoding["raw"]
            start = first(row, ("start", "startNs", "start_ns", "begin", "timestamp"))
            end = first(row, ("end", "endNs", "end_ns", "finish"))
            duration = (
                int(end) - int(start)
                if isinstance(start, (int, float)) and isinstance(end, (int, float))
                else None
            )
            raw_name = first(row, ("text", "message", "name", "demangledName", "shortName",
                                   "nameId", "textId", "messageId"))
            name = strings.get(int(raw_name), str(raw_name)) if isinstance(raw_name, (int, float)) else raw_name
            if name is None:
                name = first(row, ("eventClass", "syncType", "overheadType"))
            nvtx_marker = parse_nvtx_marker(name) if table == "NVTX_EVENTS" else None
            nvtx_marker_scope = nvtx_marker["scope"] if nvtx_marker else None
            if nvtx_marker is not None:
                row["_nepenthes_nvtx_marker"] = nvtx_marker
                if nvtx_marker_scope == "request":
                    attributed_request_token = nvtx_marker["token"]
                    attribution_level, attribution_status = "exact", "marker_identity"
                    attributed_batch_token = None
                    batch_attribution_level, batch_attribution_status = None, "not_applicable"
                else:
                    attributed_request_token = None
                    attribution_level, attribution_status = None, "not_applicable"
                    attributed_batch_token = nvtx_marker["token"]
                    batch_attribution_level, batch_attribution_status = "exact", "marker_identity"
            elif kind in ("cuda_kernel", "cuda_memcpy", "cuda_memset"):
                (
                    attributed_request_token, attribution_level, attribution_status,
                    attributed_batch_token, batch_attribution_level, batch_attribution_status,
                ) = attribute_nsys_activity(
                    start, end, nvtx_windows,
                    first(row, ("globalPid", "global_pid", "processId", "pid"))
                )
            else:
                attributed_request_token, attribution_level, attribution_status = (
                    None, None, "not_applicable"
                )
                attributed_batch_token, batch_attribution_level, batch_attribution_status = (
                    None, None, "not_applicable"
                )
            row["_nepenthes_attribution"] = {
                "request_token": attributed_request_token,
                "request_level": attribution_level,
                "request_status": attribution_status,
                "batch_token": attributed_batch_token,
                "batch_level": batch_attribution_level,
                "batch_status": batch_attribution_status,
            }
            activity_id += 1
            activities.append((
                import_id, activity_id, table, kind,
                sqlite_numeric(start, field=f"{table}.start"),
                sqlite_numeric(end, field=f"{table}.end"),
                sqlite_numeric(duration, field=f"{table}.duration"),
                sqlite_numeric(first(row, ("correlationId", "correlation_id")), field=f"{table}.correlation_id"),
                sqlite_numeric(first(row, ("globalPid", "global_pid")), field=f"{table}.global_pid"),
                sqlite_numeric(first(row, ("processId", "pid")), field=f"{table}.process_id"),
                sqlite_numeric(first(row, ("deviceId", "device_id")), field=f"{table}.device_id"),
                sqlite_numeric(first(row, ("contextId", "context_id")), field=f"{table}.context_id"),
                sqlite_numeric(first(row, ("streamId", "stream_id")), field=f"{table}.stream_id"),
                str(name) if name is not None else None,
                sqlite_numeric(enum_decoding["copy_kind_value"], field=f"{table}.copy_kind_value"),
                enum_decoding["copy_kind_name"],
                sqlite_numeric(enum_decoding["src_kind_value"], field=f"{table}.src_kind_value"),
                enum_decoding["src_kind_name"],
                sqlite_numeric(enum_decoding["dst_kind_value"], field=f"{table}.dst_kind_value"),
                enum_decoding["dst_kind_name"],
                enum_decoding["enum_decode_status"],
                sqlite_numeric(nvtx_marker["token"] if nvtx_marker else None, field=f"{table}.nvtx_correlation_token"),
                nvtx_marker["phase"] if nvtx_marker else None,
                sqlite_numeric(nvtx_marker["request_id"] if nvtx_marker else None, field=f"{table}.nvtx_marker_request_id"),
                sqlite_numeric(attributed_request_token, field=f"{table}.attributed_request_token"),
                attribution_level,
                attribution_status,
                sqlite_numeric(attributed_batch_token, field=f"{table}.attributed_batch_token"),
                batch_attribution_level,
                batch_attribution_status,
                nvtx_marker_scope,
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
                 event_count,activity_count,event_kinds_json,activity_kinds_json,correlation_policy,enum_tables_json,nsys_clock_calibration_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (import_id, run_ids[0], str(jsonl.resolve()), sha256(jsonl),
                 str(nsys.resolve()), sha256(nsys), len(events), len(activities),
                 json.dumps(dict(event_counts), sort_keys=True),
                 json.dumps(dict(activity_counts), sort_keys=True),
                 "No automatic JSONL-to-Nsight join by proximity. Token-matched NVTX markers calibrate host↔Nsight time; GPU activities receive windowed attribution only when uniquely contained in an explicit request window.",
                 json.dumps(enum_metadata, ensure_ascii=False, sort_keys=True),
                 json.dumps(nsys_clock_calibration, ensure_ascii=False, sort_keys=True)),
            )
            out.executemany(
                """INSERT INTO nepenthes_events
                (import_id,event_id,run_id,source,schema_version,timestamp_unix_ns,
                 monotonic_ns,request_id,event_kind,label,value0,value1,duration_ns,flags,
                 correlation_token,attribution_level,backend,memory_kind,memcpy_kind,
                 raw_memcpy_kind,sync_type,kv_op,raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [(import_id, e["event_id"], e["run_id"], e["source"],
                  e["schema_version"],
                  sqlite_numeric(e["timestamp_unix_ns"], field="timestamp_unix_ns"),
                  sqlite_numeric(e["monotonic_ns"], field="monotonic_ns"),
                  sqlite_numeric(e["request_id"], field="request_id"),
                  e["event_kind"], e["label"],
                  sqlite_numeric(e["value0"], field="value0"),
                  sqlite_numeric(e["value1"], field="value1"),
                  sqlite_numeric(e["duration_ns"], field="duration_ns"),
                  sqlite_numeric(e["flags"], field="flags"),
                  sqlite_numeric(e.get("correlation_token"), field="correlation_token"),
                  e.get("attribution_level"), e.get("backend"), e.get("memory_kind"),
                  e.get("memcpy_kind"),
                  sqlite_numeric(e.get("raw_memcpy_kind"), field="raw_memcpy_kind"),
                  e.get("sync_type"), e.get("kv_op"),
                  json.dumps(e, ensure_ascii=False, sort_keys=True)) for e in events],
            )
            out.executemany(
                """INSERT INTO nsys_activities
                (import_id,activity_id,source_table,activity_kind,start_ns,end_ns,duration_ns,
                 correlation_id,global_pid,process_id,device_id,context_id,stream_id,name,
                 copy_kind_value,copy_kind_name,src_kind_value,src_kind_name,dst_kind_value,
                 dst_kind_name,enum_decode_status,nvtx_correlation_token,nvtx_marker_phase,
                 nvtx_marker_request_id,attributed_request_token,attribution_level,attribution_status,raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", activities
            )
    finally:
        out.close()

    return {
        "import_id": import_id, "run_id": run_ids[0],
        "event_count": len(events), "event_kinds": dict(event_counts),
        "activity_count": len(activities), "activity_kinds": dict(activity_counts),
        "recognized_nsys_tables": sorted(t for t in NSYS_TABLES if t in names),
        "enum_tables": enum_metadata,
        "enum_decode_status_counts": dict(Counter(a[20] for a in activities)),
        "nvtx_marker_count": len(nsys_markers),
        "request_windows": len(nvtx_windows),
        "attribution_status_counts": dict(Counter(a[26] for a in activities)),
        "nsys_clock_calibration": nsys_clock_calibration,
        "output": str(output.resolve()),
        "correlation": "explicit token-matched NVTX markers only; GPU activity attribution is windowed and rejected when windows overlap",
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
        enum_maps, enum_metadata = load_enum_tables(source, names)
        nsys_markers = collect_nsys_nvtx_markers(source, names, strings)
        nvtx_windows = build_nvtx_token_windows(nsys_markers)
        nsys_clock_calibration = {
            "matched_marker_pairs": 0,
            "nsight_clock_calibrated": False,
            "reason": "standalone Nsight import has no paired JSONL host markers",
        }
        detected: dict[str, int] = {}
        for table in sorted(names):
            if table.lower().startswith("cupti_activity_kind_") or table == "NVTX_EVENTS":
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
                enum_decoding = decode_activity_enums(row, enum_maps)
                row["_nepenthes_enum_decoding"] = enum_decoding["raw"]
                start = first(row, ("start", "startNs", "start_ns", "begin", "timestamp"))
                end = first(row, ("end", "endNs", "end_ns", "finish"))
                duration = (
                    int(end) - int(start)
                    if isinstance(start, (int, float)) and isinstance(end, (int, float))
                    else None
                )
                raw_name = first(row, ("text", "message", "name", "demangledName", "shortName",
                                       "nameId", "textId", "messageId"))
                if isinstance(raw_name, (int, float)):
                    name = strings.get(int(raw_name), str(raw_name))
                else:
                    name = raw_name
                if name is None:
                    name = first(row, ("eventClass", "syncType", "overheadType"))
                nvtx_marker = parse_nvtx_marker(name) if table == "NVTX_EVENTS" else None
                nvtx_marker_scope = nvtx_marker["scope"] if nvtx_marker else None
                if nvtx_marker is not None:
                    row["_nepenthes_nvtx_marker"] = nvtx_marker
                    if nvtx_marker_scope == "request":
                        attributed_request_token = nvtx_marker["token"]
                        attribution_level, attribution_status = "exact", "marker_identity"
                        attributed_batch_token = None
                        batch_attribution_level, batch_attribution_status = None, "not_applicable"
                    else:
                        attributed_request_token = None
                        attribution_level, attribution_status = None, "not_applicable"
                        attributed_batch_token = nvtx_marker["token"]
                        batch_attribution_level, batch_attribution_status = "exact", "marker_identity"
                elif kind in ("cuda_kernel", "cuda_memcpy", "cuda_memset"):
                    (
                        attributed_request_token, attribution_level, attribution_status,
                        attributed_batch_token, batch_attribution_level, batch_attribution_status,
                    ) = attribute_nsys_activity(
                        start, end, nvtx_windows,
                        first(row, ("globalPid", "global_pid", "processId", "pid"))
                    )
                else:
                    attributed_request_token, attribution_level, attribution_status = (
                        None, None, "not_applicable"
                    )
                    attributed_batch_token, batch_attribution_level, batch_attribution_status = (
                        None, None, "not_applicable"
                    )
                row["_nepenthes_attribution"] = {
                    "request_token": attributed_request_token,
                    "request_level": attribution_level,
                    "request_status": attribution_status,
                    "batch_token": attributed_batch_token,
                    "batch_level": batch_attribution_level,
                    "batch_status": batch_attribution_status,
                }
                activity_id += 1
                activities.append((
                    import_id, activity_id, table, kind,
                    sqlite_numeric(start, field=f"{table}.start"),
                    sqlite_numeric(end, field=f"{table}.end"),
                    sqlite_numeric(duration, field=f"{table}.duration"),
                    sqlite_numeric(first(row, ("correlationId", "correlation_id")), field=f"{table}.correlation_id"),
                    sqlite_numeric(first(row, ("globalPid", "global_pid")), field=f"{table}.global_pid"),
                    sqlite_numeric(first(row, ("processId", "pid")), field=f"{table}.process_id"),
                    sqlite_numeric(first(row, ("deviceId", "device_id")), field=f"{table}.device_id"),
                    sqlite_numeric(first(row, ("contextId", "context_id")), field=f"{table}.context_id"),
                    sqlite_numeric(first(row, ("streamId", "stream_id")), field=f"{table}.stream_id"),
                    str(name) if name is not None else None,
                    sqlite_numeric(enum_decoding["copy_kind_value"], field=f"{table}.copy_kind_value"),
                    enum_decoding["copy_kind_name"],
                    sqlite_numeric(enum_decoding["src_kind_value"], field=f"{table}.src_kind_value"),
                    enum_decoding["src_kind_name"],
                    sqlite_numeric(enum_decoding["dst_kind_value"], field=f"{table}.dst_kind_value"),
                    enum_decoding["dst_kind_name"],
                    enum_decoding["enum_decode_status"],
                    sqlite_numeric(nvtx_marker["token"] if nvtx_marker else None, field=f"{table}.nvtx_correlation_token"),
                    nvtx_marker["phase"] if nvtx_marker else None,
                    sqlite_numeric(nvtx_marker["request_id"] if nvtx_marker else None, field=f"{table}.nvtx_marker_request_id"),
                    sqlite_numeric(attributed_request_token, field=f"{table}.attributed_request_token"),
                    attribution_level,
                    attribution_status,
                    sqlite_numeric(attributed_batch_token, field=f"{table}.attributed_batch_token"),
                    batch_attribution_level,
                    batch_attribution_status,
                    nvtx_marker_scope,
                    json.dumps(row, ensure_ascii=False, sort_keys=True),
                ))
                activity_counts[kind] += 1
    finally:
        source.close()

    if not activities:
        raise ValueError("Nsight SQLite contains no supported CUPTI activity rows or NVTX events")
    unsupported = {table: count for table, count in detected.items() if table not in NSYS_TABLES and count > 0}
    coverage = {
        "supported_tables": sorted(table for table in detected if table in NSYS_TABLES),
        "unsupported_tables": sorted(unsupported),
        "unsupported_row_count": sum(unsupported.values()),
        "detected_cupti_tables": sum(1 for table in detected if table.lower().startswith("cupti_activity_kind_")),
        "detected_nvtx_tables": int("NVTX_EVENTS" in detected),
        "nvtx_marker_rows": len(nsys_markers),
        "imported_activity_rows": len(activities),
        "status": "partial" if unsupported else "complete_for_detected_supported_tables",
    }

    out = sqlite3.connect(output)
    try:
        init_output(out)
        with out:
            out.execute(
                """INSERT INTO nepenthes_nsys_imports
                (import_id,nsys_path,nsys_sha256,activity_count,activity_kinds_json,
                 detected_table_counts_json,coverage_json,provenance,correlation_policy,enum_tables_json,
                 nsys_clock_calibration_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (import_id, str(nsys.resolve()), sha256(nsys), len(activities),
                 json.dumps(dict(activity_counts), sort_keys=True),
                 json.dumps(detected, sort_keys=True), json.dumps(coverage, sort_keys=True),
                 "standalone_nsys_capture_without_paired_nepenthes_jsonl",
                 "No NEPENTHES run_id or paired host↔Nsight clock calibration. Explicit NVTX token windows may support windowed GPU attribution within the Nsight clock domain only.",
                 json.dumps(enum_metadata, ensure_ascii=False, sort_keys=True),
                 json.dumps(nsys_clock_calibration, ensure_ascii=False, sort_keys=True)),
            )
            out.executemany(
                """INSERT INTO nepenthes_nsys_activities
                (import_id,activity_id,source_table,activity_kind,start_ns,end_ns,duration_ns,
                 correlation_id,global_pid,process_id,device_id,context_id,stream_id,name,
                 copy_kind_value,copy_kind_name,src_kind_value,src_kind_name,dst_kind_value,
                 dst_kind_name,enum_decode_status,nvtx_correlation_token,nvtx_marker_phase,
                 nvtx_marker_request_id,attributed_request_token,attribution_level,attribution_status,raw_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", activities
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
        "enum_tables": enum_metadata,
        "enum_decode_status_counts": dict(Counter(a[20] for a in activities)),
        "nvtx_marker_count": len(nsys_markers),
        "request_windows": len(nvtx_windows),
        "attribution_status_counts": dict(Counter(a[26] for a in activities)),
        "nsys_clock_calibration": nsys_clock_calibration,
        "coverage": coverage,
        "output": str(output.resolve()),
        "correlation": "no paired host clock calibration; only explicit NVTX windows within the Nsight clock domain are used",
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
