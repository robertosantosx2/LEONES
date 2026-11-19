from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.nepenthes_aiperf_import import import_aiperf


def write_summary(root: Path) -> None:
    summary = {
        "schema_version": "1.7",
        "aiperf_version": "0.13.0",
        "benchmark_id": "bench-001",
        "start_time": "2026-11-19T07:00:00Z",
        "end_time": "2026-11-19T07:00:10Z",
        "request_latency": {"unit": "ms", "avg": 42.5, "min": 30.0, "p50": 40.0, "p99": 60.0, "count": 2},
        "time_to_first_token": {"unit": "ms", "avg": 12.0, "count": 2},
        "request_throughput": {"unit": "requests/sec", "avg": 0.2},
        "input_config": {"endpoint": {"url": "http://127.0.0.1:8080"}},
        "run_info": {"benchmark_id": "bench-001", "random_seed": 17, "cli_command": "aiperf profile --model test"},
    }
    (root / "profile_export_aiperf.json").write_text(json.dumps(summary), encoding="utf-8")


def write_records(root: Path) -> None:
    records = [
        {
            "metadata": {
                "session_num": 0, "x_request_id": "req-001",
                "x_correlation_id": "corr-001", "conversation_id": "conv-001",
                "turn_index": 0, "request_start_ns": 1_800_000_000_000_000_000,
                "request_end_ns": 1_800_000_000_100_000_000, "benchmark_phase": "profiling",
            },
            "metrics": {
                "time_to_first_token": {"value": 15.5, "unit": "ms"},
                "inter_token_latency": {"value": 4.25, "unit": "ms"},
                "inter_chunk_latency": {"value": [4.0, 4.5], "unit": "ms"},
            },
            "error": None,
        },
        {
            "metadata": {"session_num": 1, "x_request_id": "req-002", "turn_index": 0, "was_cancelled": True},
            "metrics": {"error_isl": {"value": 64, "unit": "tokens"}},
            "error": {"code": 499, "type": "RequestCancellationError", "message": "cancelled"},
        },
    ]
    (root / "profile_export.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )


def test_imports_summary_and_request_records_without_private_payloads(tmp_path: Path):
    artifacts = tmp_path / "aiperf-artifacts"
    output = tmp_path / "nepenthes-import"
    artifacts.mkdir()
    write_summary(artifacts)
    write_records(artifacts)
    (artifacts / "outputs.json").write_text(
        json.dumps({"data": [{"response_text": "must not be imported"}]}), encoding="utf-8"
    )

    report = import_aiperf(artifacts, output)
    events = [json.loads(line) for line in (output / "aiperf_events.jsonl").read_text(encoding="utf-8").splitlines()]

    assert report["run_id"] == "bench-001"
    assert report["aiperf_version"] == "0.13.0"
    assert report["summary_metric_count"] == 3
    assert report["request_count"] == 2
    assert report["failed_request_count"] == 1
    assert report["request_metric_count"] == 4
    assert report["event_count"] == 8
    assert report["privacy"] == {
        "prompts_imported": False, "generated_text_imported": False,
        "credentials_imported": False, "raw_payloads_imported": False,
    }
    assert any(item["path"] == "outputs.json" and item["sha256"] for item in report["source_artifacts"])
    assert not any("response_text" in event for event in events)
    request_event = next(event for event in events if event.get("request_id") == "req-001" and event.get("metric_name") == "inter_chunk_latency")
    assert request_event["value"] == [4.0, 4.5]
    assert request_event["timestamp_unix_ns"] == 1_800_000_000_000_000_000
    assert request_event["monotonic_ns"] is None
    assert request_event["source_tool"] == "aiperf"
    error_event = next(event for event in events if event["event_kind"] == "aiperf_request_error")
    assert error_event["error"]["code"] == 499


def test_event_ids_are_stable_across_reimports(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    write_summary(artifacts)
    write_records(artifacts)
    first = tmp_path / "first"
    second = tmp_path / "second"
    import_aiperf(artifacts, first)
    import_aiperf(artifacts, second)
    ids1 = [json.loads(line)["event_id"] for line in (first / "aiperf_events.jsonl").read_text().splitlines()]
    ids2 = [json.loads(line)["event_id"] for line in (second / "aiperf_events.jsonl").read_text().splitlines()]
    assert ids1 == ids2


def test_rejects_malformed_jsonl_without_claiming_success(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "profile_export.jsonl").write_text('{"metadata":{}}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSONL"):
        import_aiperf(artifacts, tmp_path / "out")
    assert not (tmp_path / "out" / "aiperf_import_report.json").exists()


def test_rejects_ambiguous_multiple_summaries(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    (artifacts / "nested").mkdir(parents=True)
    write_summary(artifacts)
    write_summary(artifacts / "nested")
    with pytest.raises(ValueError, match="multiple candidate artifacts"):
        import_aiperf(artifacts, tmp_path / "out")


def test_rejects_output_nested_inside_source_artifacts(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    write_summary(artifacts)
    with pytest.raises(ValueError, match="must not be inside"):
        import_aiperf(artifacts, artifacts / "imported")


def test_rejects_empty_artifact_directory(tmp_path: Path):
    artifacts = tmp_path / "empty"
    artifacts.mkdir()
    with pytest.raises(ValueError, match="no supported AIPerf artifacts"):
        import_aiperf(artifacts, tmp_path / "out")