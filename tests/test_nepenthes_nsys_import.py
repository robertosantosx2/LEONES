from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.nepenthes_nsys_import import import_all


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
