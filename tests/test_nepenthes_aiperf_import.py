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


def write_server_metrics(root: Path) -> None:
    records = [{
        "endpoint_url": "http://user:secret@127.0.0.1:8080/metrics?token=do-not-leak",
        "timestamp_ns": 1_800_000_000_200_000_000,
        "endpoint_latency_ns": 1_000_000,
        "request_sent_ns": 1_800_000_000_199_000_000,
        "first_byte_ns": 1_800_000_000_199_500_000,
        "benchmark_phase": "profiling",
        "phase_index": 0,
        "metrics": {
            "llama_prompt_tokens_total": [
                {"labels": {"model": "qwen-local", "request_id": "private-request"}, "value": 128}
            ],
            "llama_request_duration_seconds": [
                {"labels": {"model": "qwen-local"}, "buckets": {"0.5": 2, "+Inf": 3}, "sum": 1.25, "count": 3}
            ],
        },
    }]
    (root / "server_metrics_export.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )


def write_gpu_telemetry(root: Path) -> None:
    record = {
        "timestamp_ns": 1_800_000_000_300_000_000,
        "telemetry_source_url": "pynvml://ssantos-msi",
        "gpu_uuid": "GPU-test-uuid",
        "gpu_index": 0,
        "gpu_model_name": "NVIDIA RTX 3050 Laptop GPU",
        "pci_bus_id": "00000000:01:00.0",
        "device": "nvidia0",
        "hostname": "ssantos-msi",
        "platform": "nvidia",
        "namespace": "private-namespace",
        "pod_name": "private-pod",
        "telemetry_data": {
            "nvidia_power_usage": 42.0,
            "nvidia_energy_consumption": 1.25,
            "nvidia_gpu_utilization": 35.0,
            "private_custom_metric": "must-not-export",
        },
    }
    (root / "gpu_telemetry_export.jsonl").write_text(json.dumps(record) + "\n", encoding="utf-8")



def write_server_metrics_aggregate(root: Path) -> None:
    payload = {
        "schema_version": "1.1",
        "aiperf_version": "0.13.0",
        "benchmark_id": "bench-001",
        "summary": {
            "phase_time_ranges": {
                "profiling": {"start_ns": 1_800_000_000_000_000_000, "end_ns": 1_800_000_000_500_000_000},
                "warmup": {"start_ns": 1_799_999_999_000_000_000, "end_ns": 1_799_999_999_500_000_000},
            }
        },
        "metrics_phase": "profiling",
        "metrics": {
            "llama_active_slots": {
                "type": "gauge", "description": "Active slots", "unit": "requests",
                "series": [{
                    "endpoint_url": "http://user:secret@127.0.0.1:8080/metrics?token=do-not-leak",
                    "labels": {"model": "qwen-local", "request_id": "private-request"},
                    "stats": {"avg": 1.0, "min": 0.0, "max": 2.0, "p99": 2.0},
                    "timeslices": [{"start_ns": 100, "end_ns": 200, "avg": 1.5}],
                }],
            },
            "llama_requests_total": {
                "type": "counter", "description": "Requests", "unit": "requests",
                "series": [{
                    "endpoint_url": "http://127.0.0.1:8080/metrics",
                    "labels": {"model": "qwen-local"},
                    "stats": {"total": 5.0, "rate": 0.5},
                }],
            },
            "llama_request_latency_seconds": {
                "type": "histogram", "description": "Latency", "unit": "seconds",
                "series": [{
                    "endpoint_url": "http://127.0.0.1:8080/metrics",
                    "labels": {"model": "qwen-local"},
                    "stats": {"count": 5, "sum": 1.25, "avg": 0.25, "p99_estimate": 0.5},
                    "buckets": {"0.5": 4, "+Inf": 5},
                }],
            },
        },
        "warmup_metrics": {
            "llama_active_slots": {
                "type": "gauge", "description": "Active slots", "unit": "requests",
                "series": [{
                    "endpoint_url": "http://127.0.0.1:8080/metrics",
                    "labels": {"model": "qwen-local"},
                    "stats": {"avg": 0.0, "max": 0.0},
                }],
            }
        },
    }
    (root / "server_metrics_export.json").write_text(json.dumps(payload), encoding="utf-8")



def test_imports_summary_and_request_records_without_private_payloads(tmp_path: Path):
    artifacts = tmp_path / "aiperf-artifacts"
    output = tmp_path / "nepenthes-import"
    artifacts.mkdir()
    write_summary(artifacts)
    write_records(artifacts)
    write_server_metrics(artifacts)
    write_server_metrics_aggregate(artifacts)
    write_gpu_telemetry(artifacts)
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
    assert report["event_count"] == 17
    assert report["server_metric_aggregate_count"] == 4
    assert report["server_metric_record_count"] == 1
    assert report["server_metric_sample_count"] == 2
    assert report["gpu_telemetry_record_count"] == 1
    assert report["gpu_telemetry_metric_count"] == 3
    assert report["privacy"] == {
        "prompts_imported": False, "generated_text_imported": False,
        "credentials_imported": False, "raw_payloads_imported": False,
        "request_identifiers_pseudonymized": True, "gpu_uuid_raw_exported": False,
        "pci_bus_id_raw_exported": False, "error_payloads_redacted": True,
    }
    assert any(item["path"] == "outputs.json" and item["sha256"] for item in report["source_artifacts"])
    assert not any("response_text" in event for event in events)
    assert "server_metrics_export.jsonl" == report["server_metrics_file"]
    assert "gpu_telemetry_export.jsonl" == report["gpu_telemetry_file"]
    assert "server_metrics_export.json" == report["server_metrics_summary_file"]
    server_event = next(event for event in events if event["event_kind"] == "aiperf_server_metric_sample" and event["metric_shape"] == "histogram")
    assert server_event["buckets"] == {"0.5": 2, "+Inf": 3}
    assert server_event["endpoint_origin"] == "http://127.0.0.1:8080"
    assert server_event["timestamp_unix_ns"] == 1_800_000_000_200_000_000
    aggregate = next(event for event in events if event["event_kind"] == "aiperf_server_metric_aggregate" and event["metric_name"] == "llama_active_slots")
    assert aggregate["endpoint_origin"] == "http://127.0.0.1:8080"
    assert aggregate["statistics"]["p99"] == 2.0
    assert aggregate["window_start_unix_ns"] == 1_800_000_000_000_000_000
    assert any(event["scope"] == "server_warmup_aggregate" for event in events)
    gpu_energy = next(event for event in events if event["event_kind"] == "aiperf_gpu_telemetry" and event["metric_name"] == "nvidia_energy_consumption")
    assert gpu_energy["value"] == 1.25 and gpu_energy["unit"] == "MJ"
    assert gpu_energy["value_semantics"] == "cumulative_counter"
    assert gpu_energy["device_attribution"] == "device_level_not_process_level"
    serialized_events = json.dumps(events)
    for private_value in ("secret", "do-not-leak", "private-request", "ssantos-msi", "private-namespace", "private-pod", "must-not-export"):
        assert private_value not in serialized_events
    request_event = next(event for event in events if event.get("event_kind") == "aiperf_metric" and event.get("metric_name") == "inter_chunk_latency")
    assert request_event["value"] == [4.0, 4.5]
    assert request_event["request_id"] != "req-001"  # raw request identifiers are pseudonymized
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


def test_prefers_root_aggregate_and_preserves_phase_summaries(tmp_path: Path):
    artifacts = tmp_path / "artifacts"
    (artifacts / "phases" / "baseline").mkdir(parents=True)
    write_summary(artifacts)
    write_summary(artifacts / "phases" / "baseline")
    report = import_aiperf(artifacts, tmp_path / "out")
    assert report["summary_file"] == "profile_export_aiperf.json"
    assert "phases/baseline/profile_export_aiperf.json" in report["preserved_unparsed_phase_files"]
    assert any("phase-scoped summary exports" in warning for warning in report["warnings"])


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

def test_imports_server_and_gpu_telemetry_without_summary_or_request_records(tmp_path: Path):
    artifacts = tmp_path / "telemetry-only"
    artifacts.mkdir()
    write_server_metrics(artifacts)
    write_gpu_telemetry(artifacts)
    report = import_aiperf(artifacts, tmp_path / "out")
    assert report["summary_file"] is None
    assert report["records_file"] is None
    assert report["server_metric_sample_count"] == 2
    assert report["gpu_telemetry_metric_count"] == 3
    assert report["event_count"] == 5
    assert any("summary JSON not present" in warning for warning in report["warnings"])


def test_rejects_malformed_gpu_telemetry_record(tmp_path: Path):
    artifacts = tmp_path / "bad-gpu"
    artifacts.mkdir()
    (artifacts / "gpu_telemetry_export.jsonl").write_text(
        json.dumps({"timestamp_ns": 123, "telemetry_data": "not-an-object"}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="no telemetry_data object"):
        import_aiperf(artifacts, tmp_path / "out")
    assert not (tmp_path / "out" / "aiperf_import_report.json").exists()




def test_imports_server_aggregate_without_other_artifacts(tmp_path: Path):
    artifacts = tmp_path / "aggregate-only"
    artifacts.mkdir()
    write_server_metrics_aggregate(artifacts)
    report = import_aiperf(artifacts, tmp_path / "out")
    assert report["summary_file"] is None
    assert report["server_metrics_summary_file"] == "server_metrics_export.json"
    assert report["server_metric_aggregate_count"] == 4
    assert report["event_count"] == 4


def test_rejects_unknown_server_aggregate_schema(tmp_path: Path):
    artifacts = tmp_path / "unknown-schema"
    artifacts.mkdir()
    (artifacts / "server_metrics_export.json").write_text(
        json.dumps({"schema_version": "9.0", "metrics": {}}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="unsupported AIPerf server metrics JSON schema"):
        import_aiperf(artifacts, tmp_path / "out")


