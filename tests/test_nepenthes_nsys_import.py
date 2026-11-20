from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from scripts.nepenthes_nsys_import import event_rows, import_all, import_nsys_only, inspect_nsys


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




def write_jsonl_v11(path: Path, *, backend: str | None = "cuda") -> None:
    event = {
        "schema_version": "1.1",
        "run_id": "qwen35-typed",
        "event_id": "llama-1",
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_000_000,
        "monotonic_ns": 123456,
        "request_id": 42,
        "correlation_token": 77,
        "attribution_level": "exact",
        "backend": backend,
        "memory_kind": "device",
        "memcpy_kind": "host_to_device",
        "raw_memcpy_kind": 1,
        "sync_type": "stream",
        "kv_op": None,
        "clock_domain": "steady_clock",
        "event_kind": "transfer",
        "label": "cuda.memcpy.h2d_sync",
        "value0": 4096,
        "value1": 0,
        "duration_ns": 1200,
        "flags": 0,
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
        CREATE TABLE ENUM_CUDA_MEMCPY_OPER(id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO ENUM_CUDA_MEMCPY_OPER VALUES (1, 'HTOD'), (2, 'DTOH');
        CREATE TABLE ENUM_CUDA_MEM_KIND(id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO ENUM_CUDA_MEM_KIND VALUES (1, 'PAGEABLE'), (2, 'PINNED'), (3, 'DEVICE');
        CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(
            start INTEGER, end INTEGER, correlationId INTEGER,
            deviceId INTEGER, contextId INTEGER, streamId INTEGER,
            bytes INTEGER, copyKind INTEGER, srcKind INTEGER, dstKind INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY
        VALUES (1700, 1900, 43, 0, 1, 7, 4096, 1, 1, 3);
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
    memcpy = db.execute(
        "SELECT copy_kind_value,copy_kind_name,src_kind_value,src_kind_name,"
        "dst_kind_value,dst_kind_name,enum_decode_status FROM nsys_activities "
        "WHERE activity_kind='cuda_memcpy'"
    ).fetchone()
    assert memcpy == (1, "HTOD", 1, "PAGEABLE", 3, "DEVICE", "decoded")
    enum_json = json.loads(db.execute(
        "SELECT enum_tables_json FROM nepenthes_imports"
    ).fetchone()[0])
    assert enum_json["ENUM_CUDA_MEMCPY_OPER"]["mapping"]["1"] == "HTOD"
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
    assert report["enum_tables"]["ENUM_CUDA_MEMCPY_OPER"]["mapping"]["1"] == "HTOD"
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
        CREATE TABLE ENUM_CUDA_MEMCPY_OPER(id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO ENUM_CUDA_MEMCPY_OPER VALUES (1, 'HTOD');
        CREATE TABLE ENUM_CUDA_MEM_KIND(id INTEGER PRIMARY KEY, name TEXT);
        INSERT INTO ENUM_CUDA_MEM_KIND VALUES (1, 'PAGEABLE'), (3, 'DEVICE');
        CREATE TABLE CUPTI_ACTIVITY_KIND_MEMCPY(
            start INTEGER, end INTEGER, correlationId INTEGER, deviceId INTEGER,
            contextId INTEGER, streamId INTEGER, bytes INTEGER, copyKind INTEGER,
            srcKind INTEGER, dstKind INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_MEMCPY VALUES (55, 59, 12, 0, 1, 2, 1024, 1, 1, 3);
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
    assert summary["activity_count"] == 5
    assert summary["activity_kinds"] == {
        "cuda_graph_trace": 1,
        "cuda_synchronization": 1,
        "cuda_event": 1,
        "cuda_memcpy": 1,
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
        assert record[1] == 5
        assert "without_paired_nepenthes_jsonl" in record[2]
        assert "No NEPENTHES run_id" in record[3]
        rows = {}
        for kind in ("cuda_graph_trace", "cuda_synchronization", "cuda_event", "cuda_memcpy", "cuda_overhead"):
            rows[kind] = db.execute(
                "SELECT activity_kind,start_ns,end_ns,duration_ns,name "
                "FROM nepenthes_nsys_activities WHERE activity_kind=?",
                (kind,),
            ).fetchone()
        assert rows["cuda_graph_trace"][:4] == ("cuda_graph_trace", 10, 40, 30)
        assert rows["cuda_synchronization"][:4] == ("cuda_synchronization", 41, 50, 9)
        assert rows["cuda_event"][:4] == ("cuda_event", 51, None, None)
        assert rows["cuda_memcpy"][:4] == ("cuda_memcpy", 55, 59, 4)
        assert rows["cuda_overhead"][:4] == ("cuda_overhead", 60, 70, 10)
        memcpy = db.execute(
            "SELECT copy_kind_name,src_kind_name,dst_kind_name,enum_decode_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_memcpy'"
        ).fetchone()
        assert memcpy == ("HTOD", "PAGEABLE", "DEVICE", "decoded")
        coverage = json.loads(db.execute(
            "SELECT coverage_json FROM nepenthes_nsys_imports"
        ).fetchone()[0])
        assert coverage["unsupported_tables"] == ["CUPTI_ACTIVITY_KIND_FUTURE_UNMAPPED"]



def test_memcpy_unsigned_sentinel_is_preserved_without_fake_enum_label(tmp_path: Path):
    nsys = tmp_path / "sentinel.sqlite"
    output = tmp_path / "sentinel-import.sqlite"
    write_nsys(nsys)
    with sqlite3.connect(nsys) as source:
        source.execute("UPDATE CUPTI_ACTIVITY_KIND_MEMCPY SET srcKind=-1")
    summary = import_nsys_only(nsys, output, "sentinel-enum-import")
    assert summary["enum_decode_status_counts"]["partial"] == 1
    with sqlite3.connect(output) as db:
        row = db.execute(
            "SELECT src_kind_value,src_kind_name,enum_decode_status,raw_json "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_memcpy'"
        ).fetchone()
    assert row[:3] == (-1, None, "partial")
    raw = json.loads(row[3])
    assert raw["srcKind"] == -1
    assert raw["_nepenthes_enum_decoding"]["src_kind"]["value"] == -1
    assert raw["_nepenthes_enum_decoding"]["src_kind"]["label"] is None


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

def test_import_preserves_uint64_sentinel_in_raw_json(tmp_path: Path):
    jsonl = tmp_path / "uint64.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl)
    event = json.loads(jsonl.read_text(encoding="utf-8"))
    event["value0"] = 2**64 - 1
    event["value1"] = 2**64 - 1
    jsonl.write_text(json.dumps(event) + chr(10), encoding="utf-8")
    write_nsys(nsys)

    summary = import_all(jsonl, nsys, output, "uint64-import")
    assert summary["event_count"] == 1

    with sqlite3.connect(output) as db:
        value0, value1, raw_json = db.execute(
            "SELECT value0,value1,raw_json FROM nepenthes_events"
        ).fetchone()

    assert value0 == -1
    assert value1 == -1
    raw = json.loads(raw_json)
    assert raw["value0"] == 2**64 - 1
    assert raw["value1"] == 2**64 - 1


def test_import_rejects_integer_outside_uint64_range(tmp_path: Path):
    jsonl = tmp_path / "overflow.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl)
    event = json.loads(jsonl.read_text(encoding="utf-8"))
    event["value0"] = 2**64
    jsonl.write_text(json.dumps(event) + chr(10), encoding="utf-8")
    write_nsys(nsys)

    with pytest.raises(ValueError, match="outside the supported"):
        import_all(jsonl, nsys, output, "overflow-import")


def test_import_converts_all_jsonl_uint64_integer_fields(tmp_path: Path):
    jsonl = tmp_path / "uint64-fields.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl)
    event = json.loads(jsonl.read_text(encoding="utf-8"))
    fields = ("timestamp_unix_ns", "monotonic_ns", "request_id",
              "value0", "value1", "duration_ns", "flags")
    for field in fields:
        event[field] = 2**64 - 1
    jsonl.write_text(json.dumps(event) + chr(10), encoding="utf-8")
    write_nsys(nsys)

    import_all(jsonl, nsys, output, "uint64-fields-import")
    with sqlite3.connect(output) as db:
        row = db.execute(
            "SELECT timestamp_unix_ns,monotonic_ns,request_id,value0,value1,duration_ns,flags,raw_json "
            "FROM nepenthes_events"
        ).fetchone()
    assert row[:7] == (-1, -1, -1, -1, -1, -1, -1)
    raw = json.loads(row[7])
    assert all(raw[field] == 2**64 - 1 for field in fields)


def test_nsys_only_reimport_with_same_import_id_is_rejected_without_overwrite(tmp_path: Path):
    nsys = tmp_path / "historical.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_extended_nsys(nsys)
    import_nsys_only(nsys, output, "repeatable-id")
    before = output.read_bytes()
    with pytest.raises(sqlite3.IntegrityError):
        import_nsys_only(nsys, output, "repeatable-id")
    assert output.read_bytes() == before


def write_nvtx_nsys(path: Path) -> None:
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE NVTX_EVENTS(
            start INTEGER, end INTEGER, text TEXT, globalPid INTEGER
        );
        INSERT INTO NVTX_EVENTS VALUES
            (1110, 1110, 'nepenthes.request.start token=77 request=42', 99),
            (5110, 5110, 'nepenthes.request.end token=77 request=42', 99);
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
            start INTEGER, end INTEGER, correlationId INTEGER,
            globalPid INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, name TEXT
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES
            (1500, 1600, 101, 99, 0, 1, 7, 'inside_request'),
            (5200, 5300, 102, 99, 0, 1, 7, 'outside_request');
    """)
    db.commit()
    db.close()


def write_jsonl_nvtx(path: Path) -> None:
    records = []
    for event_id, phase, before, after in (
        ("host-start", "start", 100, 120),
        ("host-end", "end", 4100, 4120),
    ):
        records.append({
            "schema_version": "1.0",
            "run_id": "paired-nvtx",
            "event_id": event_id,
            "source": "llama.cpp",
            "timestamp_unix_ns": 2_000_000_000 + after,
            "monotonic_ns": after,
            "request_id": 42,
            "correlation_token": 77,
            "attribution_level": "exact",
            "clock_domain": "steady_clock",
            "event_kind": "nvtx_marker",
            "label": f"request.{phase}",
            "value0": before,
            "value1": after,
            "duration_ns": 0,
            "flags": 1 if phase == "start" else 2,
        })
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_nsys_only_attributes_only_inside_explicit_nvtx_windows(tmp_path: Path):
    nsys = tmp_path / "nvtx.sqlite"
    output = tmp_path / "nvtx-only.sqlite"
    write_nvtx_nsys(nsys)

    summary = import_nsys_only(nsys, output, "nvtx-only-001")
    assert summary["nvtx_marker_count"] == 2
    assert summary["request_windows"] == 1
    assert summary["coverage"]["detected_nvtx_tables"] == 1

    with sqlite3.connect(output) as db:
        kernels = db.execute(
            "SELECT start_ns,attributed_request_token,attribution_level,attribution_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_kernel' ORDER BY start_ns"
        ).fetchall()
        markers = db.execute(
            "SELECT nvtx_correlation_token,nvtx_marker_phase,attribution_level "
            "FROM nepenthes_nsys_activities WHERE activity_kind='nvtx_event' ORDER BY start_ns"
        ).fetchall()
    assert kernels == [
        (1500, 77, "windowed", "unique_explicit_request_window"),
        (5200, None, None, "outside_request_window"),
    ]
    assert markers == [(77, "start", "exact"), (77, "end", "exact")]


def test_paired_nvtx_markers_calibrate_host_to_nsys_clock(tmp_path: Path):
    jsonl = tmp_path / "trace.jsonl"
    nsys = tmp_path / "nvtx.sqlite"
    output = tmp_path / "paired.sqlite"
    write_jsonl_nvtx(jsonl)
    write_nvtx_nsys(nsys)

    summary = import_all(jsonl, nsys, output, "paired-nvtx-001")
    calibration = summary["nsys_clock_calibration"]
    assert calibration["matched_marker_pairs"] == 2
    assert calibration["nsight_clock_calibrated"] is True
    assert calibration["offset_start_ns"] == 1000
    assert calibration["offset_end_ns"] == 1000
    assert calibration["drift_ppm"] == 0
    assert calibration["host_bracket_uncertainty_ns"] == 10

    with sqlite3.connect(output) as db:
        stored = json.loads(db.execute(
            "SELECT nsys_clock_calibration_json FROM nepenthes_imports"
        ).fetchone()[0])
        kernel = db.execute(
            "SELECT attributed_request_token,attribution_level FROM nsys_activities "
            "WHERE activity_kind='cuda_kernel' AND start_ns=1500"
        ).fetchone()
    assert stored["matched_marker_pairs"] == 2
    assert kernel == (77, "windowed")




def test_overlapping_explicit_nvtx_windows_are_not_attributed(tmp_path: Path):
    nsys = tmp_path / "overlap.sqlite"
    output = tmp_path / "overlap-import.sqlite"
    db = sqlite3.connect(nsys)
    db.executescript("""
        CREATE TABLE NVTX_EVENTS(start INTEGER, end INTEGER, text TEXT, globalPid INTEGER);
        INSERT INTO NVTX_EVENTS VALUES
            (1000, 1000, 'nepenthes.request.start token=77 request=42', 99),
            (5000, 5000, 'nepenthes.request.end token=77 request=42', 99),
            (1400, 1400, 'nepenthes.request.start token=88 request=43', 99),
            (1700, 1700, 'nepenthes.request.end token=88 request=43', 99);
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER, end INTEGER, correlationId INTEGER, globalPid INTEGER);
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (1500, 1600, 9, 99);
    """)
    db.commit()
    db.close()

    summary = import_nsys_only(nsys, output, "overlap-import")
    assert summary["request_windows"] == 2
    with sqlite3.connect(output) as db:
        row = db.execute(
            "SELECT attributed_request_token,attribution_level,attribution_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_kernel'"
        ).fetchone()
    assert row == (None, None, "overlapping_request_windows")




def test_cli_verifier_accepts_importer_nvtx_clock_contract():
    import importlib.util

    cli_path = Path(__file__).resolve().parents[1] / "scripts" / "nepenthes.py"
    spec = importlib.util.spec_from_file_location("nepenthes_cli_contract", cli_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    events = [
        {"event_kind": "clock_calibration", "label": "clock.calibration.start",
         "monotonic_ns": 100, "timestamp_unix_ns": 1000, "clock_domain": "steady_clock"},
        {"event_kind": "request_start", "correlation_token": 77, "attribution_level": "exact"},
        {"event_kind": "nvtx_marker", "label": "request.start", "correlation_token": 77,
         "attribution_level": "exact", "clock_domain": "steady_clock",
         "timestamp_unix_ns": 1100, "value0": 101, "value1": 105},
        {"event_kind": "nvtx_marker", "label": "request.end", "correlation_token": 77,
         "attribution_level": "exact", "clock_domain": "steady_clock",
         "timestamp_unix_ns": 1900, "value0": 901, "value1": 905},
        {"event_kind": "request_end", "correlation_token": 77, "attribution_level": "exact"},
        {"event_kind": "clock_calibration", "label": "clock.calibration.end",
         "monotonic_ns": 1000, "timestamp_unix_ns": 1900, "clock_domain": "steady_clock"},
    ]
    summary, errors = module.validate_event_contract(events)
    assert errors == []
    assert summary["nvtx_tokens"] == 1
    assert summary["host_clock_calibration"]["calibrated"] is True




def test_nsys_window_attribution_is_scoped_to_the_originating_process(tmp_path: Path):
    nsys = tmp_path / "multi-process.sqlite"
    output = tmp_path / "multi-process-import.sqlite"
    db = sqlite3.connect(nsys)
    db.executescript("""
        CREATE TABLE NVTX_EVENTS(start INTEGER, end INTEGER, text TEXT, globalPid INTEGER);
        INSERT INTO NVTX_EVENTS VALUES
            (1000, 1000, 'nepenthes.request.start token=77 request=42', 99),
            (5000, 5000, 'nepenthes.request.end token=77 request=42', 99);
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(start INTEGER, end INTEGER, correlationId INTEGER, globalPid INTEGER);
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES
            (1500, 1600, 9, 99),
            (1500, 1600, 10, 100);
    """)
    db.commit()
    db.close()

    import_nsys_only(nsys, output, "multi-process-import")
    with sqlite3.connect(output) as db:
        rows = db.execute(
            "SELECT global_pid,attributed_request_token,attribution_level,attribution_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_kernel' ORDER BY global_pid"
        ).fetchall()
    assert rows == [
        (99, 77, "windowed", "unique_explicit_request_window"),
        (100, None, None, "missing_process_request_window"),
    ]


def test_import_persists_schema_v11_typed_engine_metadata(tmp_path: Path):
    jsonl = tmp_path / "typed-trace.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "typed-normalized.sqlite"
    write_jsonl_v11(jsonl)
    write_nsys(nsys)

    import_all(jsonl, nsys, output, "typed-import-001")
    db = sqlite3.connect(output)
    event = db.execute(
        "SELECT correlation_token,attribution_level,backend,memory_kind,memcpy_kind,"
        "raw_memcpy_kind,sync_type,kv_op FROM nepenthes_events"
    ).fetchone()
    assert event == (77, "exact", "cuda", "device", "host_to_device", 1, "stream", None)
    raw = json.loads(db.execute("SELECT raw_json FROM nepenthes_events").fetchone()[0])
    assert raw["schema_version"] == "1.1"
    db.close()


def test_event_rows_accepts_schema_v11_sink_summary(tmp_path: Path):
    jsonl = tmp_path / "typed-with-summary.jsonl"
    write_jsonl_v11(jsonl)
    summary = {
        "schema_version": "1.1",
        "run_id": "qwen35-typed",
        "event_id": "llama-2",
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_000_100,
        "monotonic_ns": 123556,
        "request_id": 0,
        "correlation_token": None,
        "attribution_level": None,
        "backend": None,
        "memory_kind": None,
        "memcpy_kind": None,
        "raw_memcpy_kind": None,
        "sync_type": None,
        "kv_op": None,
        "clock_domain": "steady_clock",
        "event_kind": "sink_summary",
        "label": "sink.summary",
        "value0": 1,
        "value1": 0,
        "duration_ns": 0,
        "flags": 0,
        "events_drained": 1,
        "dropped_events": 0,
        "write_errors": 0,
    }
    with jsonl.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(summary) + "\n")
    events = list(event_rows(jsonl))
    assert [event["event_kind"] for event in events] == ["transfer", "sink_summary"]


def test_event_rows_rejects_unknown_schema_v11_backend(tmp_path: Path):
    jsonl = tmp_path / "invalid-typed-trace.jsonl"
    write_jsonl_v11(jsonl, backend="mystery-accelerator")
    with pytest.raises(ValueError, match="invalid backend"):
        list(event_rows(jsonl))


def test_typed_event_schema_migration_is_idempotent(tmp_path: Path):
    jsonl = tmp_path / "typed-trace.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "typed-normalized.sqlite"
    write_jsonl_v11(jsonl)
    write_nsys(nsys)

    import_all(jsonl, nsys, output, "typed-import-first")
    import_all(jsonl, nsys, output, "typed-import-second")
    db = sqlite3.connect(output)
    count = db.execute("SELECT COUNT(*) FROM nepenthes_events").fetchone()[0]
    assert count == 2
    columns = {row[1] for row in db.execute("PRAGMA table_info(nepenthes_events)")}
    assert {"backend", "memory_kind", "memcpy_kind", "raw_memcpy_kind", "kv_op"} <= columns
    db.close()


def write_batch_nvtx_nsys(path: Path, kernel_thread_id: int = 777) -> None:
    db = sqlite3.connect(path)
    db.executescript(f"""
        CREATE TABLE NVTX_EVENTS(
            start INTEGER, end INTEGER, text TEXT, globalPid INTEGER, globalTid INTEGER
        );
        INSERT INTO NVTX_EVENTS VALUES
            (1110, 1110, 'nepenthes.batch.start token=123', 99, 777),
            (5110, 5110, 'nepenthes.batch.end token=123', 99, 777),
            (1120, 1120, 'nepenthes.request.start token=123 request=42', 99, 777),
            (1910, 1910, 'nepenthes.request.end token=123 request=42', 99, 777);
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
            start INTEGER, end INTEGER, correlationId INTEGER,
            globalPid INTEGER, globalTid INTEGER, deviceId INTEGER, contextId INTEGER,
            streamId INTEGER, name TEXT
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES
            (1500, 1600, 201, 99, {kernel_thread_id}, 0, 1, 7, 'inside_request_and_batch'),
            (2500, 2600, 202, 99, {kernel_thread_id}, 0, 1, 7, 'inside_batch_only'),
            (5200, 5300, 203, 99, {kernel_thread_id}, 0, 1, 7, 'outside_batch');
    """)
    db.commit()
    db.close()


def write_batch_jsonl_nvtx(path: Path) -> None:
    records = []
    markers = (
        ("batch-start", "batch.start", 100, 120, 0),
        ("batch-end", "batch.end", 4100, 4120, 0),
        ("request-start", "request.start", 110, 130, 42),
        ("request-end", "request.end", 900, 920, 42),
    )
    for event_id, label, before, after, request_id in markers:
        records.append({
            "schema_version": "1.0",
            "run_id": "paired-batch",
            "event_id": event_id,
            "source": "tandem.cpp",
            "timestamp_unix_ns": 2_000_000_000 + after,
            "monotonic_ns": after,
            "request_id": request_id,
            "correlation_token": 123,
            "attribution_level": "exact",
            "clock_domain": "steady_clock",
            "event_kind": "nvtx_marker",
            "label": label,
            "value0": before,
            "value1": after,
            "duration_ns": 0,
            "flags": 1 if label.endswith(".start") else 2,
        })
    for event_id, request_id, slot_id, task_id in (
        ("member-42", 42, 0, 41),
        ("member-43", 43, 1, 42),
    ):
        records.append({
            "schema_version": "1.0",
            "run_id": "paired-batch",
            "event_id": event_id,
            "source": "tandem.cpp",
            "timestamp_unix_ns": 2_000_000_500,
            "monotonic_ns": 500,
            "request_id": request_id,
            "correlation_token": 123,
            "attribution_level": "exact",
            "clock_domain": "steady_clock",
            "event_kind": "routing",
            "label": "server.batch_member",
            "value0": slot_id,
            "value1": task_id,
            "duration_ns": 0,
            "flags": 1,
        })
    path.write_text("".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")


def test_batch_nvtx_scope_preserves_many_to_many_request_activity_membership(tmp_path: Path):
    jsonl = tmp_path / "batch-trace.jsonl"
    nsys = tmp_path / "batch-nsys.sqlite"
    output = tmp_path / "batch-paired.sqlite"
    write_batch_jsonl_nvtx(jsonl)
    write_batch_nvtx_nsys(nsys)

    summary = import_all(jsonl, nsys, output, "batch-paired-001")
    assert summary["nvtx_marker_count"] == 4
    assert summary["request_windows"] == 1
    assert summary["batch_windows"] == 1
    assert summary["nsys_clock_calibration"]["matched_marker_pairs"] == 4
    assert summary["nsys_clock_calibration"]["nsight_clock_calibrated"] is True

    with sqlite3.connect(output) as db:
        kernels = db.execute(
            "SELECT start_ns,attributed_request_token,attributed_batch_token,"
            "attribution_level,batch_attribution_level,attribution_status,batch_attribution_status "
            "FROM nsys_activities WHERE activity_kind='cuda_kernel' ORDER BY start_ns"
        ).fetchall()
        members = db.execute(
            "SELECT start_ns,request_id,slot_id,task_id,correlation_token,batch_attribution_level "
            "FROM nepenthes_batch_activity_membership ORDER BY start_ns,request_id"
        ).fetchall()
        marker_scopes = db.execute(
            "SELECT nvtx_marker_scope,COUNT(*) FROM nsys_activities "
            "WHERE activity_kind='nvtx_event' GROUP BY nvtx_marker_scope ORDER BY nvtx_marker_scope"
        ).fetchall()

    assert kernels == [
        (1500, 123, 123, "windowed", "windowed",
         "unique_explicit_request_window", "unique_explicit_batch_window"),
        (2500, None, 123, None, "windowed",
         "outside_request_window", "unique_explicit_batch_window"),
        (5200, None, None, None, None,
         "outside_request_window", "outside_batch_window"),
    ]
    assert members == [
        (1500, 42, 0, 41, 123, "windowed"),
        (1500, 43, 1, 42, 123, "windowed"),
        (2500, 42, 0, 41, 123, "windowed"),
        (2500, 43, 1, 42, 123, "windowed"),
    ]
    assert marker_scopes == [("batch", 2), ("request", 2)]


def test_nsys_only_rejects_overlapping_batch_windows(tmp_path: Path):
    nsys = tmp_path / "overlapping-batches.sqlite"
    output = tmp_path / "overlapping-batches-output.sqlite"
    db = sqlite3.connect(nsys)
    db.executescript("""
        CREATE TABLE NVTX_EVENTS(
            start INTEGER, end INTEGER, text TEXT, globalPid INTEGER, globalTid INTEGER
        );
        INSERT INTO NVTX_EVENTS VALUES
            (1000, 1000, 'nepenthes.batch.start token=123', 99, 777),
            (3000, 3000, 'nepenthes.batch.end token=123', 99, 777),
            (1200, 1200, 'nepenthes.batch.start token=124', 99, 777),
            (3200, 3200, 'nepenthes.batch.end token=124', 99, 777);
        CREATE TABLE CUPTI_ACTIVITY_KIND_KERNEL(
            start INTEGER, end INTEGER, correlationId INTEGER, globalPid INTEGER, globalTid INTEGER
        );
        INSERT INTO CUPTI_ACTIVITY_KIND_KERNEL VALUES (1500, 1600, 9, 99, 777);
    """)
    db.commit()
    db.close()

    summary = import_nsys_only(nsys, output, "overlapping-batch-import")
    assert summary["batch_windows"] == 2
    with sqlite3.connect(output) as db:
        row = db.execute(
            "SELECT attributed_batch_token,batch_attribution_level,batch_attribution_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_kernel'"
        ).fetchone()
    assert row == (None, None, "overlapping_batch_windows")


def test_batch_attribution_rejects_activity_from_another_host_thread(tmp_path: Path):
    nsys = tmp_path / "wrong-batch-thread.sqlite"
    output = tmp_path / "wrong-batch-thread-output.sqlite"
    write_batch_nvtx_nsys(nsys, kernel_thread_id=778)

    summary = import_nsys_only(nsys, output, "wrong-batch-thread-import")
    assert summary["batch_windows"] == 1
    with sqlite3.connect(output) as db:
        rows = db.execute(
            "SELECT attributed_batch_token,batch_attribution_level,batch_attribution_status "
            "FROM nepenthes_nsys_activities WHERE activity_kind='cuda_kernel' ORDER BY start_ns"
        ).fetchall()
    assert rows == [
        (None, None, "no_matching_batch_thread_window"),
        (None, None, "no_matching_batch_thread_window"),
        (None, None, "no_matching_batch_thread_window"),
    ]


def test_import_accepts_native_schema_v10_sink_summary_and_preserves_source(tmp_path: Path):
    jsonl = tmp_path / "native-summary.jsonl"
    nsys = tmp_path / "capture.sqlite"
    output = tmp_path / "normalized.sqlite"
    write_jsonl(jsonl, request_id=23)
    write_nsys(nsys)
    summary_record = {
        "schema_version": "1.0",
        "run_id": "qwen35-test",
        "event_id": "llama-2",
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_100_000,
        "event_kind": "sink_summary",
        "events_drained": 1,
        "dropped_events": 0,
        "write_errors": 0,
    }
    with jsonl.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(summary_record) + "\n")

    imported = import_all(jsonl, nsys, output, "native-summary-import")
    assert imported["event_count"] == 2
    assert imported["event_kinds"]["sink_summary"] == 1

    with sqlite3.connect(output) as db:
        row = db.execute(
            "SELECT event_kind,label,monotonic_ns,request_id,value0,value1,duration_ns,flags,raw_json "
            "FROM nepenthes_events WHERE event_kind='sink_summary'"
        ).fetchone()
    assert row[:8] == ("sink_summary", "sink.summary", 0, 0, 1, 0, 0, 0)
    assert json.loads(row[8]) == summary_record


def test_sink_summary_rejects_mismatched_count_and_nonterminal_position(tmp_path: Path):
    jsonl = tmp_path / "invalid-summary.jsonl"
    write_jsonl(jsonl)
    summary_record = {
        "schema_version": "1.0",
        "run_id": "qwen35-test",
        "event_id": "summary-1",
        "source": "llama.cpp",
        "timestamp_unix_ns": 1_800_000_000_000_100_000,
        "event_kind": "sink_summary",
        "events_drained": 2,
        "dropped_events": 0,
        "write_errors": 0,
    }
    with jsonl.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(summary_record) + "\\n")
    with pytest.raises(ValueError, match="events_drained does not match"):
        list(event_rows(jsonl))

    summary_record["events_drained"] = 1
    with jsonl.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps({
            "schema_version": "1.0", "run_id": "qwen35-test",
            "event_id": "tandem-2", "source": "tandem.cpp",
            "timestamp_unix_ns": 1_800_000_000_000_000_001,
            "monotonic_ns": 123457, "request_id": 0,
            "event_kind": "kv_cache", "label": "kv.update",
            "value0": 1, "value1": 1, "duration_ns": 1, "flags": 0
        }) + "\\n")
