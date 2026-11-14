#!/usr/bin/env python3
"""Inspect a Nsight Systems SQLite export without modifying it.

The report keeps CUDA Runtime API time separate from GPU kernel and memcpy
activity. CUPTI enum values are decoded using CUpti_ActivityMemcpyKind and
CUpti_ActivityMemoryKind, not cudaMemcpyKind.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sqlite3
from urllib.parse import quote

MEMCPY_KIND = {
    0: "UNKNOWN", 1: "HTOD", 2: "DTOH", 3: "HTOA", 4: "ATOH",
    5: "ATOA", 6: "ATOD", 7: "DTOA", 8: "DTOD", 9: "HTOH", 10: "PTOP",
}
MEMORY_KIND = {
    0: "UNKNOWN", 1: "PAGEABLE", 2: "PINNED", 3: "DEVICE",
    4: "ARRAY", 5: "MANAGED", 6: "DEVICE_STATIC", 7: "MANAGED_STATIC",
}


def _connect_readonly(path: pathlib.Path) -> sqlite3.Connection:
    uri = "file:" + quote(str(path.resolve())) + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _tables(db: sqlite3.Connection) -> set[str]:
    return {
        row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }


def _columns(db: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in db.execute(f'PRAGMA table_info("{table}")')}


def _strings(db: sqlite3.Connection, tables: set[str]) -> dict[int, str]:
    if "StringIds" not in tables:
        return {}
    return {int(i): str(value) for i, value in db.execute(
        "SELECT id, value FROM StringIds"
    )}


def _duration_stats(rows: list[int]) -> dict:
    if not rows:
        return {"count": 0, "total_ms": 0.0, "mean_us": None, "max_us": None}
    return {
        "count": len(rows),
        "total_ms": round(sum(rows) / 1e6, 3),
        "mean_us": round(sum(rows) / len(rows) / 1e3, 3),
        "max_us": round(max(rows) / 1e3, 3),
    }


def analyze_database(path: pathlib.Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)

    with _connect_readonly(path) as db:
        tables = _tables(db)
        strings = _strings(db, tables)
        report = {
            "input": str(path),
            "tables": sorted(tables),
            "table_counts": {},
            "runtime": {"available": False},
            "kernels": {"available": False},
            "memcpy": {"available": False},
            "moe_wait_sequence": {"available": False},
            "cpu_sampling": {
                "candidate_tables": sorted(
                    name for name in tables
                    if any(token in name.upper() for token in
                           ("SAMPLE", "SCHED", "OSRT", "CPU_ACTIVITY"))
                ),
                "interpretation": (
                    "Candidate table names only; inspect their schemas and "
                    "contents before claiming CPU sampling or scheduler coverage."
                ),
            },
        }

        for table in (
            "CUPTI_ACTIVITY_KIND_RUNTIME",
            "CUPTI_ACTIVITY_KIND_KERNEL",
            "CUPTI_ACTIVITY_KIND_MEMCPY",
            "CUPTI_ACTIVITY_KIND_SYNCHRONIZATION",
        ):
            if table in tables:
                report["table_counts"][table] = db.execute(
                    f'SELECT COUNT(*) FROM "{table}"'
                ).fetchone()[0]

        if "CUPTI_ACTIVITY_KIND_RUNTIME" in tables:
            cols = _columns(db, "CUPTI_ACTIVITY_KIND_RUNTIME")
            required = {"globalTid", "nameId", "start", "end"}
            if required <= cols:
                thread_names = {}
                if "ThreadNames" in tables:
                    thread_names = {
                        int(tid): strings.get(int(name_id), str(name_id))
                        for name_id, _priority, tid in db.execute(
                            "SELECT nameId, priority, globalTid FROM ThreadNames"
                        )
                    }
                processes = {}
                if "PROCESSES" in tables:
                    processes = {
                        int(gpid): {"pid": pid, "name": name}
                        for gpid, pid, name in db.execute(
                            "SELECT globalPid, pid, name FROM PROCESSES"
                        )
                    }

                per_thread = collections.defaultdict(list)
                per_thread_api = collections.defaultdict(
                    lambda: collections.defaultdict(list)
                )
                for tid, name_id, start, end in db.execute(
                    "SELECT globalTid, nameId, start, end "
                    "FROM CUPTI_ACTIVITY_KIND_RUNTIME"
                ):
                    duration = max(0, int(end) - int(start))
                    tid = int(tid)
                    api = strings.get(int(name_id), f"nameId:{name_id}")
                    per_thread[tid].append(duration)
                    per_thread_api[tid][api].append(duration)

                thread_rows = []
                for tid, durations in per_thread.items():
                    gpid = (tid >> 32) << 32
                    thread_rows.append({
                        "globalTid": tid,
                        "thread_name": thread_names.get(tid),
                        "process": processes.get(gpid),
                        **_duration_stats(durations),
                        "apis": [
                            {"name": api, **_duration_stats(values)}
                            for api, values in sorted(
                                per_thread_api[tid].items(),
                                key=lambda item: len(item[1]), reverse=True
                            )
                        ],
                    })
                thread_rows.sort(key=lambda row: row["count"], reverse=True)
                report["runtime"] = {
                    "available": True,
                    "total_calls": sum(row["count"] for row in thread_rows),
                    "threads": thread_rows,
                    "note": (
                        "Durations are CUDA Runtime/Driver API host intervals, "
                        "not GPU execution time."
                    ),
                }

        if "CUPTI_ACTIVITY_KIND_KERNEL" in tables:
            cols = _columns(db, "CUPTI_ACTIVITY_KIND_KERNEL")
            required = {"start", "end", "shortName"}
            if required <= cols:
                grouped = collections.defaultdict(list)
                for short_name, start, end in db.execute(
                    "SELECT shortName, start, end FROM CUPTI_ACTIVITY_KIND_KERNEL"
                ):
                    label = strings.get(int(short_name), f"shortName:{short_name}")
                    grouped[label].append(max(0, int(end) - int(start)))
                rows = [
                    {"name": name, **_duration_stats(values)}
                    for name, values in grouped.items()
                ]
                rows.sort(key=lambda row: row["total_ms"], reverse=True)
                report["kernels"] = {
                    "available": True,
                    "total_events": sum(row["count"] for row in rows),
                    "by_name": rows,
                    "note": "Kernel activity durations are GPU activity intervals.",
                }

        if "CUPTI_ACTIVITY_KIND_MEMCPY" in tables:
            cols = _columns(db, "CUPTI_ACTIVITY_KIND_MEMCPY")
            required = {"copyKind", "srcKind", "dstKind", "bytes", "start", "end"}
            if required <= cols:
                grouped = collections.defaultdict(
                    lambda: {"count": 0, "bytes": 0, "duration_ns": 0}
                )
                for copy_kind, src_kind, dst_kind, size, start, end in db.execute(
                    "SELECT copyKind, srcKind, dstKind, bytes, start, end "
                    "FROM CUPTI_ACTIVITY_KIND_MEMCPY"
                ):
                    key = (
                        MEMCPY_KIND.get(int(copy_kind), f"UNKNOWN_{copy_kind}"),
                        MEMORY_KIND.get(int(src_kind), f"UNKNOWN_{src_kind}"),
                        MEMORY_KIND.get(int(dst_kind), f"UNKNOWN_{dst_kind}"),
                    )
                    item = grouped[key]
                    item["count"] += 1
                    item["bytes"] += int(size)
                    item["duration_ns"] += max(0, int(end) - int(start))
                rows = []
                for (kind, src, dst), item in grouped.items():
                    rows.append({
                        "copy_kind": kind, "src_memory": src, "dst_memory": dst,
                        "count": item["count"], "bytes": item["bytes"],
                        "duration_ms": round(item["duration_ns"] / 1e6, 3),
                    })
                rows.sort(key=lambda row: row["bytes"], reverse=True)
                report["memcpy"] = {
                    "available": True,
                    "total_events": sum(row["count"] for row in rows),
                    "total_bytes": sum(row["bytes"] for row in rows),
                    "by_kind_and_memory": rows,
                    "enum_note": (
                        "copyKind uses CUpti_ActivityMemcpyKind; srcKind/dstKind "
                        "use CUpti_ActivityMemoryKind."
                    ),
                    "note": "Accumulated bytes are traffic, not resident memory.",
                }

        kernel_table = "CUPTI_ACTIVITY_KIND_KERNEL"
        if kernel_table in tables:
            cols = _columns(db, kernel_table)
            required = {"start", "end", "deviceId", "contextId", "streamId", "shortName"}
            wait_ids = [
                sid for sid, value in strings.items()
                if value == "k_host_add_wait"
            ]
            if required <= cols and wait_ids:
                query = (
                    "SELECT start, end, deviceId, contextId, streamId, shortName "
                    "FROM CUPTI_ACTIVITY_KIND_KERNEL "
                    "WHERE deviceId=? AND contextId=? AND streamId=? "
                    "ORDER BY start"
                )
                wait_count = 0
                patterns = collections.Counter()
                for device, context, stream in db.execute(
                    "SELECT DISTINCT deviceId, contextId, streamId "
                    "FROM CUPTI_ACTIVITY_KIND_KERNEL"
                ):
                    rows = list(db.execute(query, (device, context, stream)))
                    for index, row in enumerate(rows):
                        start, end, _device, _context, _stream, short_id = row
                        if int(short_id) not in wait_ids:
                            continue
                        wait_count += 1
                        previous = strings.get(int(rows[index - 1][5])) if index else None
                        following = strings.get(int(rows[index + 1][5])) if index + 1 < len(rows) else None
                        patterns[(previous, following)] += 1
                report["moe_wait_sequence"] = {
                    "available": True,
                    "wait_kernel": "k_host_add_wait",
                    "wait_count": wait_count,
                    "neighbor_patterns": [
                        {"previous": before, "next": after, "count": count}
                        for (before, after), count in patterns.most_common()
                    ],
                    "note": (
                        "Neighbor order is by GPU kernel start time on the same "
                        "device/context/stream. It does not identify the CPU "
                        "worker or prove the cause/duration of the wait."
                    ),
                }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=pathlib.Path, help="Nsight Systems SQLite export")
    parser.add_argument("--output", type=pathlib.Path, help="Optional JSON output path")
    args = parser.parse_args()
    result = analyze_database(args.database)
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
