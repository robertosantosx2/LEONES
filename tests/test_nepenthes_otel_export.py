from __future__ import annotations

import json

import pytest

from scripts.nepenthes_otel_export import build_otlp, load_events, metric_name, summarize_values


def fixture_events():
    metadata = {
        "request_start_ns": 1_800_000_000_000_000_000,
        "request_end_ns": 1_800_000_000_100_000_000,
        "session_num": 0, "turn_index": 0, "benchmark_phase": "profiling",
    }
    return [
        {
            "event_kind": "aiperf_metric", "scope": "request",
            "run_id": "run-001", "request_id": "req-001",
            "metric_name": "time_to_first_token", "value": 12.5, "unit": "ms",
            "timestamp_unix_ns": metadata["request_start_ns"], "metadata": metadata,
        },
        {
            "event_kind": "aiperf_metric", "scope": "request",
            "run_id": "run-001", "request_id": "req-001",
            "metric_name": "inter_token_latency", "value": [4.0, 6.0, 8.0], "unit": "ms",
            "timestamp_unix_ns": metadata["request_start_ns"], "metadata": metadata,
        },
        {
            "event_kind": "aiperf_request_error", "scope": "request",
            "run_id": "run-001", "request_id": "req-002",
            "error": {"code": 499, "type": "RequestCancellationError", "message": "private response text"},
            "timestamp_unix_ns": 1_800_000_000_200_000_000,
            "metadata": {"request_start_ns": 1_800_000_000_150_000_000,
                         "request_end_ns": 1_800_000_000_200_000_000, "session_num": 1},
        },
        {
            "event_kind": "aiperf_metric", "scope": "run_summary",
            "run_id": "run-001", "metric_name": "request_throughput",
            "value": 0.2, "unit": "requests/sec", "timestamp_unix_ns": 1_800_000_000_000_000_000,
        },
        {
            "event_kind": "aiperf_server_metric_sample", "scope": "server_timeseries",
            "run_id": "run-001", "metric_name": "llama_request_duration_seconds",
            "metric_shape": "histogram", "value": None, "buckets": {"0.5": 2, "+Inf": 3},
            "sum": 1.2, "count": 3, "unit": "s",
            "labels": {"model": "qwen-local", "request_id": "do-not-export"},
            "timestamp_unix_ns": 1_800_000_000_300_000_000,
        },
        {
            "event_kind": "aiperf_server_metric_aggregate", "scope": "server_aggregate",
            "run_id": "run-001", "metric_name": "llama_request_latency_seconds",
            "metric_type": "histogram", "unit": "s",
            "statistics": {"avg": 0.1, "p99_estimate": 0.5},
            "window_end_unix_ns": 1_800_000_000_400_000_000,
        },
        {
            "event_kind": "aiperf_gpu_telemetry", "scope": "device_sample",
            "run_id": "run-001", "metric_name": "nvidia_power_usage",
            "value": 42.0, "unit": "W", "gpu_uuid": "GPU-test",
            "gpu_model_name": "NVIDIA RTX 3050 Laptop GPU",
            "device_attribution": "device_level_not_process_level",
            "timestamp_unix_ns": 1_800_000_000_500_000_000,
        },
        {
            "event_kind": "aiperf_metric", "scope": "request",
            "run_id": "run-001", "request_id": "req-no-time",
            "metric_name": "time_to_first_token", "value": 10.0, "unit": "ms",
            "timestamp_unix_ns": None, "metadata": {},
        },
    ]


def test_builds_parent_run_and_request_spans_with_stable_trace_ids():
    traces, metrics, report = build_otlp(fixture_events())
    spans = traces["resourceSpans"][0]["scopeSpans"][0]["spans"]
    assert len(spans) == 3
    run_span = next(span for span in spans if span["name"] == "aiperf.benchmark")
    request = next(span for span in spans if span.get("attributes") and any(a["key"] == "aiperf.request_id" and a["value"].get("stringValue") == "req-001" for a in span["attributes"]))
    assert request["traceId"] == run_span["traceId"]
    assert request["parentSpanId"] == run_span["spanId"]
    assert request["kind"] == "SPAN_KIND_CLIENT"
    assert report["skipped_request_spans_missing_timestamps"] == 1


def test_request_error_becomes_error_span_without_exporting_error_message():
    traces, _, _ = build_otlp(fixture_events())
    spans = traces["resourceSpans"][0]["scopeSpans"][0]["spans"]
    error_span = next(span for span in spans if span["status"]["code"] == "STATUS_CODE_ERROR")
    encoded = json.dumps(error_span)
    assert '"stringValue":"499"' in encoded or '"intValue":"499"' in encoded
    assert "private response text" not in encoded


def test_maps_request_summary_server_histogram_and_gpu_to_otel_gauges():
    _, payload, report = build_otlp(fixture_events())
    metrics = payload["resourceMetrics"][0]["scopeMetrics"][0]["metrics"]
    names = {item["name"] for item in metrics}
    assert "aiperf.request.time_to_first_token" in names
    assert "aiperf.request.inter_token_latency.mean" in names
    assert "aiperf.request_throughput" in names
    assert "llama_server.llama_request_duration_seconds.bucket_count" in names
    assert "llama_server.llama_request_latency_seconds.p99_estimate" in names
    assert "gpu.nvidia_power_usage" in names
    assert all("gauge" in item for item in metrics)
    assert report["metric_point_count"] > 0


def test_request_ids_never_become_metric_attributes_and_private_text_is_not_exported():
    _, metrics, _ = build_otlp(fixture_events())
    encoded = json.dumps(metrics)
    assert "req-001" not in encoded
    assert "req-002" not in encoded
    assert "do-not-export" not in encoded
    assert "private response text" not in encoded
    assert "prompt" not in encoded


def test_metric_names_are_sanitized_and_list_summaries_are_deterministic():
    assert metric_name("llama:request-duration_seconds") == "llama_request_duration_seconds"
    summary = summarize_values([4.0, 6.0, 8.0])
    assert summary["mean"] == 6.0
    assert summary["p50"] == 6.0
    assert summary["p95"] == 7.8


def test_load_events_rejects_malformed_jsonl(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"event_kind":"ok"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="invalid NEPENTHES JSONL"):
        load_events(path)