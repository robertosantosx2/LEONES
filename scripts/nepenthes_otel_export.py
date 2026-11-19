#!/usr/bin/env python3
"""Convert NEPENTHES JSONL events into OTLP/JSON traces and metrics payloads.

The exporter is offline: it writes OTLP/JSON request bodies without sending
network traffic. Prompts, generated text, credentials and request IDs are never
metric attributes; request IDs are retained only on trace spans.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
SAFE_METRIC_ATTRIBUTES = {
    "model", "status", "backend", "device", "device_id", "type",
    "operation", "slot_id", "result", "method", "le", "quantile",
    "gpu_uuid", "gpu_index", "gpu_model_name", "pci_bus_id", "platform",
    "device_scope", "device_attribution", "value_semantics",
    "metric_type", "metrics_phase", "benchmark_phase", "phase_kind",
    "source_component",
}


def digest_hex(*parts: Any, length: int = 32) -> str:
    raw = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return float(value)


def otel_value(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bool):
        return {"boolValue": value}
    if isinstance(value, int):
        return {"intValue": str(value)}
    if isinstance(value, float) and math.isfinite(value):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value[:512]}
    return None


def attributes(values: dict[str, Any], *, allow: set[str] | None = None) -> list[dict[str, Any]]:
    result = []
    for key, value in sorted(values.items()):
        if allow is not None and key not in allow:
            continue
        encoded = otel_value(value)
        if encoded is not None:
            result.append({"key": str(key), "value": encoded})
    return result


def metric_name(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.]", "_", value).strip("_.")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = "nepenthes_" + cleaned
    return cleaned[:240]


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def summarize_values(value: Any) -> dict[str, float] | None:
    if not isinstance(value, list):
        return None
    numbers = [number for item in value if (number := finite_number(item)) is not None]
    if not numbers:
        return None
    return {
        "count": float(len(numbers)),
        "mean": sum(numbers) / len(numbers),
        "min": min(numbers), "max": max(numbers),
        "p50": percentile(numbers, 0.50),
        "p95": percentile(numbers, 0.95),
        "p99": percentile(numbers, 0.99),
    }


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid NEPENTHES JSONL at line {line_number}: {exc}") from exc
            if not isinstance(event, dict):
                raise ValueError(f"NEPENTHES event at line {line_number} must be an object")
            events.append(event)
    return events


def metric_attributes(event: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    labels = event.get("labels")
    if isinstance(labels, dict):
        result.update({key: value for key, value in labels.items() if key in SAFE_METRIC_ATTRIBUTES})
    for key in SAFE_METRIC_ATTRIBUTES:
        value = event.get(key)
        if value is not None:
            result[key] = value
    return result


def build_otlp(events: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    grouped_requests: dict[tuple[str, str], list[dict[str, Any]]] = {}
    run_request_ranges: dict[str, list[tuple[int, int]]] = {}
    for event in events:
        if event.get("scope") == "request" and event.get("request_id") is not None:
            run_id = str(event.get("run_id") or "unknown-run")
            request_id = str(event["request_id"])
            grouped_requests.setdefault((run_id, request_id), []).append(event)

    spans_by_run: dict[str, list[dict[str, Any]]] = {}
    skipped_spans = 0
    failed_requests = 0
    for (run_id, request_id), request_events in grouped_requests.items():
        metadata = next((item.get("metadata") for item in request_events if isinstance(item.get("metadata"), dict)), {})
        start_ns = metadata.get("request_start_ns") if isinstance(metadata, dict) else None
        end_ns = metadata.get("request_end_ns") if isinstance(metadata, dict) else None
        if isinstance(start_ns, bool) or not isinstance(start_ns, int) or isinstance(end_ns, bool) or not isinstance(end_ns, int) or end_ns <= start_ns:
            skipped_spans += 1
            continue
        run_request_ranges.setdefault(run_id, []).append((start_ns, end_ns))
        trace_id = digest_hex("trace", run_id, length=32)
        parent_id = digest_hex("run-span", run_id, length=16)
        span_id = digest_hex("request-span", run_id, request_id, length=16)
        error_event = next((item for item in request_events if item.get("event_kind") == "aiperf_request_error"), None)
        if error_event:
            failed_requests += 1
        span_events = []
        for item in request_events:
            if item.get("event_kind") != "aiperf_metric":
                continue
            value = item.get("value")
            attrs = {"metric.name": item.get("metric_name"), "metric.unit": item.get("unit")}
            number = finite_number(value)
            if number is not None:
                attrs["metric.value"] = number
            else:
                summary = summarize_values(value)
                if summary is None:
                    continue
                attrs["metric.sample_count"] = summary["count"]
                attrs.update({f"metric.{key}": val for key, val in summary.items() if key != "count"})
            span_events.append({
                "timeUnixNano": str(end_ns),
                "name": "aiperf.request.metric",
                "attributes": attributes(attrs),
            })
        span_attrs = {
            "nepenthes.run_id": run_id,
            "aiperf.request_id": request_id,
            "aiperf.session_num": metadata.get("session_num") if isinstance(metadata, dict) else None,
            "aiperf.turn_index": metadata.get("turn_index") if isinstance(metadata, dict) else None,
            "aiperf.benchmark_phase": metadata.get("benchmark_phase") if isinstance(metadata, dict) else None,
            "error.code": (error_event.get("error") or {}).get("code") if error_event and isinstance(error_event.get("error"), dict) else None,
            "error.type": (error_event.get("error") or {}).get("type") if error_event and isinstance(error_event.get("error"), dict) else None,
        }
        span = {
            "traceId": trace_id, "spanId": span_id, "parentSpanId": parent_id,
            "name": "llm.request", "kind": "SPAN_KIND_CLIENT",
            "startTimeUnixNano": str(start_ns), "endTimeUnixNano": str(end_ns),
            "attributes": attributes(span_attrs), "events": span_events,
            "status": {"code": "STATUS_CODE_ERROR", "message": "request failed"} if error_event else {"code": "STATUS_CODE_OK"},
            "traceFlags": 1,
        }
        spans_by_run.setdefault(run_id, []).append(span)

    resource_spans = []
    for run_id, request_spans in spans_by_run.items():
        ranges = run_request_ranges.get(run_id, [])
        start_ns = min(item[0] for item in ranges)
        end_ns = max(item[1] for item in ranges)
        trace_id = digest_hex("trace", run_id, length=32)
        run_span_id = digest_hex("run-span", run_id, length=16)
        run_span = {
            "traceId": trace_id, "spanId": run_span_id,
            "name": "aiperf.benchmark", "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": str(start_ns), "endTimeUnixNano": str(end_ns),
            "attributes": attributes({"nepenthes.run_id": run_id, "aiperf.request_count": len(request_spans)}),
            "events": [], "status": {"code": "STATUS_CODE_OK"}, "traceFlags": 1,
        }
        resource_spans.append({
            "resource": {"attributes": attributes({"service.name": "nepenthes", "service.version": SCHEMA_VERSION})},
            "scopeSpans": [{"scope": {"name": "nepenthes.aiperf", "version": SCHEMA_VERSION}, "spans": [run_span, *request_spans]}],
        })

    metric_series: dict[tuple[str, str], dict[str, Any]] = {}
    skipped_metric_points = 0

    def add_metric(name: str, unit: str | None, value: Any, timestamp_ns: Any, attrs: dict[str, Any], description: str = "") -> None:
        nonlocal skipped_metric_points
        number = finite_number(value)
        if number is None or isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int) or timestamp_ns <= 0:
            skipped_metric_points += 1
            return
        clean_name = metric_name(name)
        clean_unit = str(unit or "")
        key = (clean_name, clean_unit)
        item = metric_series.setdefault(key, {"name": clean_name, "description": description, "unit": clean_unit, "dataPoints": []})
        item["dataPoints"].append({
            "timeUnixNano": str(timestamp_ns), "asDouble": number,
            "attributes": attributes(attrs, allow=SAFE_METRIC_ATTRIBUTES),
        })

    for event in events:
        kind = event.get("event_kind")
        timestamp_ns = event.get("timestamp_unix_ns")
        attrs = metric_attributes(event)
        if kind == "aiperf_metric":
            metric = str(event.get("metric_name") or "unknown")
            if event.get("scope") == "run_summary":
                add_metric(f"aiperf.{metric}", event.get("unit"), event.get("value"), timestamp_ns, attrs)
            elif event.get("scope") == "request":
                metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
                sample_time = metadata.get("request_end_ns") or timestamp_ns
                value = event.get("value")
                number = finite_number(value)
                if number is not None:
                    add_metric(f"aiperf.request.{metric}", event.get("unit"), number, sample_time, attrs)
                else:
                    summary = summarize_values(value)
                    if summary:
                        for stat, stat_value in summary.items():
                            add_metric(f"aiperf.request.{metric}.{stat}", event.get("unit"), stat_value, sample_time, attrs)
        elif kind in {"aiperf_server_metric_sample", "llama_server_metric"}:
            metric = str(event.get("metric_name") or "unknown")
            if finite_number(event.get("value")) is not None:
                add_metric(f"llama_server.{metric}", event.get("unit"), event.get("value"), timestamp_ns, attrs)
            buckets = event.get("buckets")
            if isinstance(buckets, dict):
                for boundary, count in buckets.items():
                    add_metric(f"llama_server.{metric}.bucket_count", "{count}", count, timestamp_ns, {**attrs, "le": boundary})
                add_metric(f"llama_server.{metric}.sum", event.get("unit"), event.get("sum"), timestamp_ns, attrs)
                add_metric(f"llama_server.{metric}.count", "{count}", event.get("count"), timestamp_ns, attrs)
        elif kind == "aiperf_server_metric_aggregate":
            metric = str(event.get("metric_name") or "unknown")
            stats = event.get("statistics") if isinstance(event.get("statistics"), dict) else {}
            for stat, value in stats.items():
                add_metric(f"llama_server.{metric}.{stat}", event.get("unit"), value, event.get("window_end_unix_ns"), attrs)
        elif kind == "aiperf_gpu_telemetry":
            add_metric(f"gpu.{event.get('metric_name', 'unknown')}", event.get("unit"), event.get("value"), timestamp_ns, attrs)
        elif kind == "nvml_device_sample":
            metrics = event.get("metrics") if isinstance(event.get("metrics"), dict) else {}
            units = {"power_w": "W", "energy_counter_mj": "mJ", "gpu_utilization_percent": "%",
                     "memory_utilization_percent": "%", "memory_used_bytes": "By", "memory_total_bytes": "By",
                     "temperature_c": "Cel", "graphics_clock_mhz": "MHz", "memory_clock_mhz": "MHz"}
            for metric, value in metrics.items():
                add_metric(f"nvml.{metric}", units.get(metric), value, timestamp_ns, attrs)

    resource_metrics = [{
        "resource": {"attributes": attributes({"service.name": "nepenthes", "service.version": SCHEMA_VERSION})},
        "scopeMetrics": [{
            "scope": {"name": "nepenthes.telemetry", "version": SCHEMA_VERSION},
            "metrics": [{
                "name": item["name"], "description": item["description"], "unit": item["unit"],
                "gauge": {"dataPoints": item["dataPoints"]},
            } for item in metric_series.values()],
        }],
    }]
    trace_payload = {"resourceSpans": resource_spans}
    metric_payload = {"resourceMetrics": resource_metrics}
    report = {
        "schema_version": SCHEMA_VERSION, "input_event_count": len(events),
        "trace_count": sum(len(item["scopeSpans"][0]["spans"]) for item in resource_spans),
        "request_span_count": sum(len(item["scopeSpans"][0]["spans"]) - 1 for item in resource_spans),
        "metric_count": sum(len(item["scopeMetrics"][0]["metrics"]) for item in resource_metrics),
        "metric_point_count": sum(len(item["dataPoints"]) for series in metric_series.values() for item in [series]),
        "skipped_request_spans_missing_timestamps": skipped_spans,
        "skipped_metric_points_missing_timestamp_or_numeric_value": skipped_metric_points,
        "privacy": {"prompts_exported": False, "generated_text_exported": False,
                    "credentials_exported": False, "request_ids_in_metric_attributes": False},
        "temporality_policy": "All exported measurements use OTLP Gauge to avoid inventing delta/cumulative semantics; histogram bucket snapshots are emitted as gauges, not OTLP histogram aggregations.",
    }
    return trace_payload, metric_payload, report


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        events = load_events(args.events)
        traces, metrics, report = build_otlp(events)
        output = args.output_dir.expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / "otlp-traces.json", traces)
        write_json(output / "otlp-metrics.json", metrics)
        write_json(output / "otlp-export-report.json", report)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())