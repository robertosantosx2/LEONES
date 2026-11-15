from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.nepenthes_nsys_import import import_all, import_nsys_only, inspect_nsys


def write_jsonl(path: Path, *, request_id: int = 0) -> None:
    event = {
        "schema_version": "1.0",
        "run_id": "qwen35-test",
        "event_id": "tandem-1",
        "source": "tandem.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_000_000,
        "monotonic_ns": 123456,
        "request_id": request_id,
        "event_kind": "kv_cache",
        "label": "kv.update",
        "value0": 4096,
        "value1": 2,
        "duration_ns": 900,
        "flags": 1,
    }
    path.write_text(json.dumps(event) + "\n", encoding="utf-8")


def write_nsys(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE StringIds(id INTEGER PRIMARY KEY, value TEXT);
        INSERT INTO StringIds VALUES (7, 'qwen_kernel');
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
            start INTEGER, end INTEGER, correlationId INTEGER,
            globalPid INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, nameId INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL
        VALUES (1000, 1600, 42, 99, 0, 1, 7, 7);
        CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(
            start INTEGER, end INTEGER, correlationId INTEGER,
            deviceId INTEGER, contextId INTEGER, streamId INTEGER,
            bytes INTEGER, copyKind INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY
        VALUES (1700, 1900, 43, 0, 1, 7, 4096, 1);
        CREATE TABLE CUPTI_ACTIVITY_KIND_RUNTIME(
            start INTEGER, end INTEGER, correlationId INTEGER, nameId INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_RUNTIME VALUES (900, 950, 42, 7);
    """)
    db.commit()
    db.close()


def test_import_preserves_events_and_nsys_activities(tmp_path: Path):
    jsonl = tmp_path / "trace.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl, request_id=23)
    write_nsys(nsys)

    summary = import_all(jsonl, nsys, output, "import-001")
    assert summary["event_count"] == 1
    assert summary["activity_count"] == 3
    assert summary["activity_kinds"] == {
        "cuda_kernel": 1, "cuda_memcpy": 1, "cuda_runtime": 1
    }

    db = sqlite3.connect(output)
    event = db.execute(
        "SELECT request_id,event_kind,label,monotonic_ns FROM nepenthes_events"
    ).fetchone()
    assert event == (23, "kv_cache", "kv.update", 123456)
    kernel = db.execute(
        "SELECT activity_kind,start_ns,end_ns,duration_ns,correlation_id,name "
        "FROM nsys_activities WHERE activity_kind='cuda_kernel'"
    ).fetchone()
    assert kernel == ("cuda_kernel", 1000, 1600, 600, 42, "qwen_kernel")
    policy = db.execute(
        "SELECT correlation_policy FROM nepenthes_imports"
    ).fetchone()[0]
    assert "No automatic JSONL-to-Nsight join" in policy
    db.close()


def test_rejects_invalid_jsonl_without_writing_import(tmp_path: Path):
    jsonl = tmp_path / "bad.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    jsonl.write_text('{"schema_version":"1.0"}\n', encoding="utf-8")
    write_nsys(nsys)

    with pytest.raises(ValueError, match="missing fields"):
        import_all(jsonl, nsys, output, "bad-import")


def test_rejects_multiple_run_ids(tmp_path: Path):
    jsonl = tmp_path / "mixed.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl)
    first = json.loads(jsonl.read_text(encoding="utf-8"))
    second = dict(first, event_id="tandem-2", run_id="other-run")
    jsonl.write_text(
        json.dumps(first) + "\n" + json.dumps(second) + "\n",
        encoding="utf-8",
    )
    write_nsys(nsys)

    with pytest.raises(ValueError, match="exactly one run_id"):
        import_all(jsonl, nsys, output, "mixed-import")


def test_rejects_duplicate_event_ids(tmp_path: Path):
    jsonl = tmp_path / "duplicate.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl)
    event = json.loads(jsonl.read_text(encoding="utf-8"))
    jsonl.write_text(
        json.dumps(event) + "\n" + json.dumps(event) + "\n",
        encoding="utf-8",
    )
    write_nsys(nsys)

    with pytest.raises(ValueError, match="duplicate event_id"):
        import_all(jsonl, nsys, output, "duplicate-import")

def test_refuses_to_overwrite_source_artifact(tmp_path: Path):
    jsonl = tmp_path / "trace.jsonl"
    nsys = tmp_path / "capture.sqlite"
    write_jsonl(jsonl)
    write_nsys(nsys)

    with pytest.raises(ValueError, match="must not overwrite"):
        import_all(jsonl, nsys, nsys, "unsafe-import")


def test_inspect_nsys_reports_schema_and_counts_without_importing(tmp_path: Path):
    nsys = tmp_path / "capture.sqlite"
    write_nsys(nsys)

    report = inspect_nsys(nsys)
    mapped = {item["table"]: item for item in report["recognized_activity_tables"]}
    assert mapped["CUPTI_ACTIVITY_KIND_KERNEL"]["row_count"] == 1
    assert mapped["CUPTI_ACTIVITY_KIND_KERNEL"]["mapped_kind"] == "cuda_kernel"
    assert "nameId" in mapped["CUPTI_ACTIVITY_KIND_KERNEL"]["columns"]
    assert report["string_tables"][0]["table"] == "StringIds"
    assert "source rows" in report["policy"]


def test_inspect_nsys_rejects_missing_file(tmp_path: Path):
    with pytest.raises(ValueError, match="does not exist"):
        inspect_nsys(tmp_path / "missing.sqlite")



def write_extended_nsys(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE StringIds(id INTEGER PRIMARY KEY, value TEXT);
        INSERT INTO StringIds VALUES (1, 'graph-node');
        CREATE TABLE CUPTI_ACTIVITY_KIND_GRAPH_TRACE(
            start INTEGER, end INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, correlationId INTEGER, globalPid INTEGER,
            graphId INTEGER, graphExecId INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_GRAPH_TRACE VALUES (10, 40, 0, 1, 2, 3, 99, 4, 5);
        CREATE TABLE CUPTI_ACTIVITY_KIND_SYNCHRONIZATION(
            start INTEGER, end INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, correlationId INTEGER, globalPid INTEGER,
            syncType INTEGER, eventId INTEGER, eventSyncId INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_SYNCHRONIZATION VALUES (41, 50, 0, 1, 2, 6, 99, 7, 8, 9);
        CREATE TABLE CUPTI_ACTIVITY_KIND_CUDA_EVENT(
            timestamp INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, correlationId INTEGER, globalPid INTEGER,
            eventId INTEGER, eventSyncId INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_CUDA_EVENT VALUES (51, 0, 1, 2, 10, 99, 11, 12);
        CREATE TABLE CUPTI_ACTIVITY_KIND_OVERHEAD(
            start INTEGER, end INTEGER, eventClass INTEGER, globalTid INTEGER,
            correlationId INTEGER, nameId INTEGER, overheadType INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_OVERHEAD VALUES (60, 70, 1, 101, 13, 1, 2);
        CREATE TABLE CUPTI_ACTIVITY_KIND_FUTURE_UNMAPPED(
            start INTEGER, end INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_FUTURE_UNMAPPED VALUES (1, 2);
    """)
    db.commit()
    db.close()


def test_nsys_only_import_preserves_extended_cupti_tables_and_provenance(tmp_path: Path):
    nsys = tmp_path / "historical.sqlite"
    output = tmp_path / "nsys-only.sqlite"
    write_extended_nsys(nsys)

    summary = import_nsys_only(nsys, output, "historical-001")
    assert summary["mode"] == "nsys_only"
    assert summary["jsonl"] is None
    assert summary["run_id"] is None
    assert summary["activity_count"] == 4
    assert summary["activity_kinds"] == {
        "cuda_graph_trace": 1,
        "cuda_synchronization": 1,
        "cuda_event": 1,
        "cuda_overhead": 1,
    }
    assert summary["coverage"]["status"] == "partial"
    assert summary["coverage"]["unsupported_row_count"] == 1

    with sqlite3.connect(output) as db:
        record = db.execute(
            "SELECT nsys_sha256,activity_count,provenance,correlation_policy "
            "FROM nepenthes_nsys_imports WHERE import_id='historical-001'"
        ).fetchone()
        assert record[0] == summary["nsys_sha256"]
        assert record[1] == 4
        assert "without_paired_nepenthes_jsonl" in record[2]
        assert "No NEPENTHES run_id" in record[3]
        rows = db.execute(
            "SELECT activity_kind,start_ns,end_ns,duration_ns,name "
            "FROM nepenthes_nsys_activities ORDER BY activity_id"
        ).fetchall()
        assert rows[0][:4] == ("cuda_graph_trace", 10, 40, 30)
        assert rows[1][:4] == ("cuda_synchronization", 41, 50, 9)
        assert rows[2][:4] == ("cuda_event", 51, None, None)
        assert rows[3][0:4] == ("cuda_overhead", 60, 70, 10)
        coverage = json.loads(db.execute(
            "SELECT coverage_json FROM nepenthes_nsys_imports"
        ).fetchone()[0])
        assert coverage["unsupported_tables"] == ["CUPTI_ACTIVITY_KIND_FUTURE_UNMAPPED"]


def test_nsys_only_import_refuses_to_overwrite_source(tmp_path: Path):
    nsys = tmp_path / "capture.sqlite"
    write_extended_nsys(nsys)
    with pytest.raises(ValueError, match="must not overwrite"):
        import_nsys_only(nsys, nsys, "unsafe")


def test_nsys_only_import_rejects_no_supported_activity(tmp_path: Path):
    nsys = tmp_path / "empty.sqlite"
    db = sqlite3.connect(nsys)
    db.execute("CREATE TABLE CUPTI_ACTIVITY_KIND_UNKNOWN(value INTEGER)")
    db.commit()
    db.close()
    with pytest.raises(ValueError, match="no supported CUPTI activity"):
        import_nsys_only(nsys, tmp_path / "out.sqlite", "empty")
