#!/usr/bin/env python3
"""Import NVIDIA AIPerf artifacts into the versioned NEPENTHES JSONL contract.

The importer is offline and read-only with respect to AIPerf source artifacts.
It deliberately does not import prompts, generated text, API credentials, or
raw request/response payloads. Unknown source fields remain in the untouched
source files and are covered by their SHA-256 inventory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from urllib.parse import urlsplit

OUTPUT_SCHEMA = "1.0"
SUMMARY_NAMES = ("profile_export_aiperf.json",)
RECORD_NAMES = ("profile_export.jsonl",)
SERVER_METRICS_NAMES = ("server_metrics_export.jsonl",)
SERVER_METRICS_SUMMARY_NAMES = ("server_metrics_export.json",)
GPU_TELEMETRY_NAMES = ("gpu_telemetry_export.jsonl",)
SAFE_PROMETHEUS_LABELS = {"model", "status", "backend", "device", "device_id", "type", "operation", "slot_id", "result", "method", "le", "quantile"}
GPU_METRICS = {
    "nvidia_power_usage": ("W", "instantaneous_power"),
    "nvidia_energy_consumption": ("MJ", "cumulative_counter"),
    "nvidia_gpu_utilization": ("%", "gauge"),
    "nvidia_memory_utilization": ("%", "gauge"),
    "nvidia_memory_used": ("GB", "gauge"),
    "nvidia_temperature": ("degC", "gauge"),
    "nvidia_sm_utilization": ("%", "gauge"),
    "nvidia_decoder_utilization": ("%", "gauge"),
    "nvidia_encoder_utilization": ("%", "gauge"),
    "nvidia_jpg_utilization": ("%", "gauge"),
    "nvidia_xid_errors": ("count", "gauge"),
    "nvidia_power_violation": ("us", "counter"),
    "amd_power": ("W", "instantaneous_power"),
    "amd_energy_consumption": ("MJ", "cumulative_counter"),
    "amd_gfx_activity": ("%", "gauge"),
    "amd_umc_activity": ("%", "gauge"),
    "amd_mm_activity": ("%", "gauge"),
    "amd_memory_used": ("GB", "gauge"),
    "amd_temperature": ("degC", "gauge"),
    "amd_ecc_uncorrectable": ("count", "counter"),
    "amd_throttle_status": ("state", "gauge"),
}
GPU_METRIC_ALIASES = {
    "gpu_power_usage": "nvidia_power_usage", "energy_consumption": "nvidia_energy_consumption",
    "gpu_utilization": "nvidia_gpu_utilization", "mem_utilization": "nvidia_memory_utilization",
    "gpu_memory_used": "nvidia_memory_used", "gpu_temperature": "nvidia_temperature",
    "sm_utilization": "nvidia_sm_utilization", "decoder_utilization": "nvidia_decoder_utilization",
    "encoder_utilization": "nvidia_encoder_utilization", "jpg_utilization": "nvidia_jpg_utilization",
    "xid_errors": "nvidia_xid_errors", "power_violation": "nvidia_power_violation",
}
SUMMARY_FIELDS = {"unit", "avg", "min", "max", "std", "count", "sum",
                  "p1", "p5", "p10", "p25", "p50", "p75", "p90", "p95", "p99"}
REQUEST_METADATA_FIELDS = (
    "session_num", "x_request_id", "x_correlation_id", "conversation_id",
    "turn_index", "request_start_ns", "request_ack_ns", "request_end_ns",
    "worker_id", "record_processor_id", "benchmark_phase", "was_cancelled",
    "cancellation_time_ns",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.replace(temporary, path)


def discover_one(root: Path, names: tuple[str, ...]) -> Path | None:
    matches = sorted(path for name in names for path in root.rglob(name)
                     if path.is_file() and not path.is_symlink())
    if not matches:
        return None
    root_matches = [path for path in matches if path.parent.resolve() == root.resolve()]
    if len(root_matches) == 1:
        return root_matches[0]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"multiple candidate artifacts found for {names}: "
                     + ", ".join(str(path) for path in matches))


def inventory(root: Path) -> list[dict[str, Any]]:
    items = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        items.append({
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    return items


def parse_timestamp_ns(value: Any) -> int | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return int(parsed.timestamp() * 1_000_000_000)


def stable_id(*parts: Any) -> str:
    payload = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]


def metric_payload(metric: Any) -> tuple[Any, str | None]:
    if isinstance(metric, dict) and "value" in metric:
        return metric.get("value"), metric.get("unit")
    if isinstance(metric, dict) and "avg" in metric:
        return metric.get("avg"), metric.get("unit")
    return metric, None



def safe_endpoint_origin(value: Any) -> str | None:
    """Keep only scheme/host/port; never export URL credentials, path, query or fragment."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        if parsed.port is not None:
            host = f"{host}:{parsed.port}"
        return f"{parsed.scheme}://{host}"
    except ValueError:
        return None


def safe_labels(value: Any) -> tuple[dict[str, str], list[str]]:
    if not isinstance(value, dict):
        return {}, []
    kept: dict[str, str] = {}
    for key, item in value.items():
        if key in SAFE_PROMETHEUS_LABELS and isinstance(item, (str, int, float)) and not isinstance(item, bool):
            kept[str(key)] = str(item)[:256]
    dropped = sorted(str(key) for key in value if key not in kept)
    return kept, dropped


def finite_number(value: Any, field: str) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number or null")
    if not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")
    return value


def iter_jsonl(path: Path, relative_name: str) -> Iterator[tuple[int, dict[str, Any]]]:
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at {relative_name}:{line_number}: {exc}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"record at {relative_name}:{line_number} must be a JSON object")
            yield line_number, record


def import_server_metrics(stream, path: Path, relative_name: str, run_id: str,
                          aiperf_version: Any, source_schema: Any) -> tuple[int, int]:
    record_count = 0
    sample_count = 0
    for line_number, record in iter_jsonl(path, relative_name):
        record_count += 1
        metrics = record.get("metrics")
        if not isinstance(metrics, dict):
            raise ValueError(f"server metrics record at {relative_name}:{line_number} has no metrics object")
        timestamp_ns = record.get("timestamp_ns")
        if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int):
            raise ValueError(f"server metrics timestamp_ns at {relative_name}:{line_number} must be an integer")
        for metric_name, samples in metrics.items():
            if not isinstance(metric_name, str) or not isinstance(samples, list):
                raise ValueError(f"invalid server metric family at {relative_name}:{line_number}")
            for sample_index, sample in enumerate(samples):
                if not isinstance(sample, dict):
                    raise ValueError(f"invalid server metric sample at {relative_name}:{line_number}")
                labels, dropped_labels = safe_labels(sample.get("labels"))
                value = finite_number(sample.get("value"), "server metric value")
                buckets_raw = sample.get("buckets")
                buckets = None
                if buckets_raw is not None:
                    if not isinstance(buckets_raw, dict):
                        raise ValueError(f"histogram buckets must be an object at {relative_name}:{line_number}")
                    buckets = {str(boundary): finite_number(count, "histogram bucket count")
                               for boundary, count in buckets_raw.items()}
                if value is None and buckets is None:
                    raise ValueError(f"server metric sample has neither value nor buckets at {relative_name}:{line_number}")
                event = {
                    "schema_version": OUTPUT_SCHEMA,
                    "event_id": stable_id(run_id, "server_metrics", relative_name, line_number, metric_name, sample_index),
                    "run_id": run_id,
                    "request_id": None,
                    "event_kind": "aiperf_server_metric_sample",
                    "scope": "server_timeseries",
                    "metric_name": metric_name,
                    "metric_shape": "histogram" if buckets is not None else "scalar",
                    "value": value,
                    "buckets": buckets,
                    "sum": finite_number(sample.get("sum"), "histogram sum"),
                    "count": finite_number(sample.get("count"), "histogram count"),
                    "unit": None,
                    "labels": labels,
                    "dropped_label_names": dropped_labels,
                    "endpoint_origin": safe_endpoint_origin(record.get("endpoint_url")),
                    "endpoint_latency_ns": record.get("endpoint_latency_ns"),
                    "request_sent_ns": record.get("request_sent_ns"),
                    "first_byte_ns": record.get("first_byte_ns"),
                    "benchmark_phase": record.get("benchmark_phase"),
                    "phase_index": record.get("phase_index"),
                    "profiling_index": record.get("profiling_index"),
                    "phase_kind": record.get("phase_kind"),
                    "timestamp_unix_ns": timestamp_ns,
                    "monotonic_ns": None,
                    "timestamp_source": "aiperf_server_metrics_timestamp_ns",
                    "source_tool": "aiperf",
                    "source_component": "llama_server",
                    "source_version": aiperf_version,
                    "source_schema_version": source_schema,
                    "source_file": relative_name,
                    "source_record_index": line_number,
                    "quality": "available",
                }
                write_event(stream, event)
                sample_count += 1
    return record_count, sample_count



def numeric_fields(value: Any) -> dict[str, int | float | bool | None]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int | float | bool | None] = {}
    for key, item in value.items():
        if item is None or isinstance(item, bool):
            result[str(key)] = item
        elif isinstance(item, (int, float)) and math.isfinite(float(item)):
            result[str(key)] = item
    return result


def safe_timeslices(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if not isinstance(item, dict):
            continue
        safe = numeric_fields(item)
        if isinstance(item.get("buckets"), dict):
            safe["buckets"] = numeric_fields(item["buckets"])
        result.append(safe)
    return result


def import_server_metrics_aggregate(stream, payload: dict[str, Any], relative_name: str,
                                    run_id: str, aiperf_version: Any) -> int:
    schema = payload.get("schema_version")
    if not isinstance(schema, str) or not schema.startswith("1."):
        raise ValueError(f"unsupported AIPerf server metrics JSON schema version: {schema!r}")
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    phase_ranges = summary.get("phase_time_ranges") if isinstance(summary.get("phase_time_ranges"), dict) else {}
    count = 0

    def emit_phase(metrics: Any, phase_name: str, scope: str) -> None:
        nonlocal count
        if metrics is None:
            return
        if not isinstance(metrics, dict):
            raise ValueError(f"{scope} server metrics must be an object")
        phase_range = phase_ranges.get(phase_name) if isinstance(phase_ranges.get(phase_name), dict) else {}
        start_ns = phase_range.get("start_ns") if isinstance(phase_range.get("start_ns"), int) else None
        end_ns = phase_range.get("end_ns") if isinstance(phase_range.get("end_ns"), int) else None
        for metric_name, metric in metrics.items():
            if not isinstance(metric_name, str) or not isinstance(metric, dict):
                raise ValueError(f"invalid aggregate server metric entry: {metric_name!r}")
            series = metric.get("series")
            if not isinstance(series, list):
                raise ValueError(f"server metric {metric_name} has no series array")
            for series_index, item in enumerate(series):
                if not isinstance(item, dict):
                    raise ValueError(f"invalid series for server metric {metric_name}")
                stats = numeric_fields(item.get("stats"))
                labels, dropped_labels = safe_labels(item.get("labels"))
                buckets = numeric_fields(item.get("buckets")) if isinstance(item.get("buckets"), dict) else None
                timeslices = safe_timeslices(item.get("timeslices"))
                event = {
                    "schema_version": OUTPUT_SCHEMA,
                    "event_id": stable_id(run_id, "server_aggregate", scope, metric_name, series_index, sorted(labels.items())),
                    "run_id": run_id,
                    "request_id": None,
                    "event_kind": "aiperf_server_metric_aggregate",
                    "scope": scope,
                    "metric_name": metric_name,
                    "metric_type": metric.get("type"),
                    "description": metric.get("description"),
                    "unit": metric.get("unit"),
                    "statistics": stats,
                    "buckets": buckets,
                    "timeslices": timeslices,
                    "endpoint_origin": safe_endpoint_origin(item.get("endpoint_url")),
                    "labels": labels,
                    "dropped_label_names": dropped_labels,
                    "window_start_unix_ns": start_ns,
                    "window_end_unix_ns": end_ns,
                    "timestamp_unix_ns": None,
                    "monotonic_ns": None,
                    "timestamp_source": "aiperf_aggregate_window",
                    "source_tool": "aiperf",
                    "source_component": "llama_server",
                    "source_version": aiperf_version,
                    "source_schema_version": schema,
                    "source_file": relative_name,
                    "source_series_index": series_index,
                    "metrics_phase": phase_name,
                    "quality": "available" if stats or buckets is not None else "series_without_statistics",
                }
                write_event(stream, event)
                count += 1

    emit_phase(payload.get("metrics"), str(payload.get("metrics_phase") or "profiling"), "server_aggregate")
    if "warmup_metrics" in payload:
        emit_phase(payload.get("warmup_metrics"), "warmup", "server_warmup_aggregate")
    return count


def import_gpu_telemetry(stream, path: Path, relative_name: str, run_id: str,
                         aiperf_version: Any, source_schema: Any) -> tuple[int, int]:
    record_count = 0
    metric_count = 0
    for line_number, record in iter_jsonl(path, relative_name):
        record_count += 1
        telemetry = record.get("telemetry_data")
        if not isinstance(telemetry, dict):
            raise ValueError(f"GPU telemetry record at {relative_name}:{line_number} has no telemetry_data object")
        timestamp_ns = record.get("timestamp_ns")
        if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int):
            raise ValueError(f"GPU telemetry timestamp_ns at {relative_name}:{line_number} must be an integer")
        device = {
            "gpu_uuid": record.get("gpu_uuid") if isinstance(record.get("gpu_uuid"), str) else None,
            "gpu_index": record.get("gpu_index") if isinstance(record.get("gpu_index"), int) and not isinstance(record.get("gpu_index"), bool) else None,
            "gpu_model_name": record.get("gpu_model_name") if isinstance(record.get("gpu_model_name"), str) else None,
            "pci_bus_id": record.get("pci_bus_id") if isinstance(record.get("pci_bus_id"), str) else None,
            "device": record.get("device") if isinstance(record.get("device"), str) else None,
            "platform": record.get("platform") if isinstance(record.get("platform"), str) else "unknown",
        }
        source_url = record.get("telemetry_source_url")
        source_protocol = urlsplit(source_url).scheme if isinstance(source_url, str) else None
        for source_name, raw_value in telemetry.items():
            metric_name = GPU_METRIC_ALIASES.get(source_name, source_name)
            if metric_name not in GPU_METRICS or raw_value is None:
                continue
            value = finite_number(raw_value, f"GPU telemetry {source_name}")
            if value is None:
                continue
            unit, semantics = GPU_METRICS[metric_name]
            event = {
                "schema_version": OUTPUT_SCHEMA,
                "event_id": stable_id(run_id, "gpu_telemetry", relative_name, line_number, metric_name),
                "run_id": run_id,
                "request_id": None,
                "event_kind": "aiperf_gpu_telemetry",
                "scope": "device_sample",
                "metric_name": metric_name,
                "value": value,
                "unit": unit,
                "value_semantics": semantics,
                **device,
                "timestamp_unix_ns": timestamp_ns,
                "monotonic_ns": None,
                "timestamp_source": "aiperf_gpu_telemetry_timestamp_ns",
                "telemetry_protocol": source_protocol,
                "device_attribution": "device_level_not_process_level",
                "source_tool": "aiperf",
                "source_component": "gpu_telemetry",
                "source_version": aiperf_version,
                "source_schema_version": source_schema,
                "source_file": relative_name,
                "source_record_index": line_number,
                "quality": "available",
            }
            write_event(stream, event)
            metric_count += 1
    return record_count, metric_count


def write_event(stream, event: dict[str, Any]) -> None:
    stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def import_aiperf(artifacts_dir: Path, output_dir: Path) -> dict[str, Any]:
    root = artifacts_dir.resolve()
    out = output_dir.resolve()
    if not root.is_dir():
        raise ValueError(f"AIPerf artifacts directory does not exist: {root}")
    if root == out or root in out.parents:
        raise ValueError("output directory must not be inside the source artifact directory")
    out.mkdir(parents=True, exist_ok=True)

    all_summary_paths = sorted(path for name in SUMMARY_NAMES for path in root.rglob(name)
                                if path.is_file() and not path.is_symlink())
    all_records_paths = sorted(path for name in RECORD_NAMES for path in root.rglob(name)
                               if path.is_file() and not path.is_symlink())
    summary_path = discover_one(root, SUMMARY_NAMES)
    records_path = discover_one(root, RECORD_NAMES)
    server_metrics_path = discover_one(root, SERVER_METRICS_NAMES)
    all_server_summary_paths = sorted(path for name in SERVER_METRICS_SUMMARY_NAMES for path in root.rglob(name) if path.is_file() and not path.is_symlink())
    server_metrics_summary_path = discover_one(root, SERVER_METRICS_SUMMARY_NAMES)
    gpu_telemetry_path = discover_one(root, GPU_TELEMETRY_NAMES)
    if summary_path is None and records_path is None and server_metrics_path is None and server_metrics_summary_path is None and gpu_telemetry_path is None:
        raise ValueError("no supported AIPerf artifacts found (summary, records, server metrics, or GPU telemetry)")

    summary: dict[str, Any] = {}
    if summary_path is not None:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read AIPerf summary {summary_path}: {exc}") from exc
        if not isinstance(summary, dict):
            raise ValueError("AIPerf summary root must be a JSON object")

    server_metrics_aggregate: dict[str, Any] = {}
    if server_metrics_summary_path is not None:
        try:
            server_metrics_aggregate = json.loads(server_metrics_summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read AIPerf server metrics summary {server_metrics_summary_path}: {exc}") from exc
        if not isinstance(server_metrics_aggregate, dict):
            raise ValueError("AIPerf server metrics summary root must be a JSON object")

    source_files = inventory(root)
    run_info = summary.get("run_info") if isinstance(summary.get("run_info"), dict) else {}
    run_id = str(summary.get("benchmark_id") or run_info.get("benchmark_id") or server_metrics_aggregate.get("benchmark_id") or
                 stable_id("aiperf-run", *(item["sha256"] for item in source_files)))
    aiperf_version = summary.get("aiperf_version") or server_metrics_aggregate.get("aiperf_version")
    source_schema = summary.get("schema_version")
    summary_rel = summary_path.relative_to(root).as_posix() if summary_path else None
    records_rel = records_path.relative_to(root).as_posix() if records_path else None
    server_metrics_rel = server_metrics_path.relative_to(root).as_posix() if server_metrics_path else None
    server_metrics_summary_rel = server_metrics_summary_path.relative_to(root).as_posix() if server_metrics_summary_path else None
    gpu_telemetry_rel = gpu_telemetry_path.relative_to(root).as_posix() if gpu_telemetry_path else None
    summary_timestamp = parse_timestamp_ns(summary.get("start_time"))
    event_path = out / "aiperf_events.jsonl"
    event_count = 0
    summary_metric_count = 0
    request_metric_count = 0
    request_count = 0
    failed_request_count = 0
    server_metric_record_count = 0
    server_metric_sample_count = 0
    server_metric_aggregate_count = 0
    gpu_telemetry_record_count = 0
    gpu_telemetry_metric_count = 0
    warnings: list[str] = []
    ignored_phase_summaries = [path for path in all_summary_paths if path != summary_path]
    ignored_phase_records = [path for path in all_records_paths if path != records_path]
    ignored_phase_server_summaries = [path for path in all_server_summary_paths if path != server_metrics_summary_path]
    if ignored_phase_summaries:
        warnings.append("phase-scoped summary exports were preserved in the source inventory but not separately normalized; the root aggregate was preferred")
    if ignored_phase_records:
        warnings.append("additional phase-scoped request JSONL files were preserved in the source inventory but not separately normalized")
    if ignored_phase_server_summaries:
        warnings.append("additional phase-scoped server metric summaries were preserved in the source inventory but not separately normalized")

    with event_path.with_name(event_path.name + ".tmp").open("w", encoding="utf-8") as stream:
        if summary_path is not None:
            for metric_name, block in summary.items():
                if not isinstance(block, dict) or "unit" not in block:
                    continue
                if not (SUMMARY_FIELDS & set(block)) or not ("avg" in block or "count" in block):
                    continue
                event = {
                    "schema_version": OUTPUT_SCHEMA,
                    "event_id": stable_id(run_id, "summary", metric_name),
                    "run_id": run_id,
                    "request_id": None,
                    "event_kind": "aiperf_metric",
                    "scope": "run_summary",
                    "metric_name": metric_name,
                    "value": block.get("avg"),
                    "unit": block.get("unit"),
                    "statistics": {key: value for key, value in block.items() if key != "unit"},
                    "timestamp_unix_ns": summary_timestamp,
                    "monotonic_ns": None,
                    "source_tool": "aiperf",
                    "source_version": aiperf_version,
                    "source_schema_version": source_schema,
                    "source_file": summary_rel,
                    "quality": "available" if block.get("avg") is not None else "summary_without_average",
                }
                write_event(stream, event)
                event_count += 1
                summary_metric_count += 1

        if records_path is not None:
            with records_path.open(encoding="utf-8") as records:
                for line_number, line in enumerate(records, start=1):
                    if not line.strip():
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"invalid JSONL at {records_rel}:{line_number}: {exc}") from exc
                    if not isinstance(record, dict):
                        raise ValueError(f"record at {records_rel}:{line_number} must be a JSON object")
                    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
                    metrics = record.get("metrics") if isinstance(record.get("metrics"), dict) else {}
                    request_id = metadata.get("x_request_id")
                    if request_id is None:
                        request_id = f"{metadata.get('session_num', line_number - 1)}:{metadata.get('turn_index', 0)}"
                    timestamp_ns = metadata.get("request_start_ns")
                    if isinstance(timestamp_ns, bool) or not isinstance(timestamp_ns, int):
                        timestamp_ns = None
                    request_count += 1
                    error = record.get("error")
                    if error:
                        failed_request_count += 1
                        event = {
                            "schema_version": OUTPUT_SCHEMA,
                            "event_id": stable_id(run_id, "request_error", request_id, line_number),
                            "run_id": run_id, "request_id": str(request_id),
                            "event_kind": "aiperf_request_error", "scope": "request",
                            "error": error, "timestamp_unix_ns": timestamp_ns,
                            "monotonic_ns": None, "source_tool": "aiperf",
                            "source_version": aiperf_version,
                            "source_schema_version": source_schema,
                            "source_file": records_rel, "source_record_index": line_number,
                            "metadata": {key: metadata.get(key) for key in REQUEST_METADATA_FIELDS if key in metadata},
                        }
                        write_event(stream, event)
                        event_count += 1
                    for metric_name, metric in metrics.items():
                        value, unit = metric_payload(metric)
                        event = {
                            "schema_version": OUTPUT_SCHEMA,
                            "event_id": stable_id(run_id, "request", request_id, metric_name, line_number),
                            "run_id": run_id, "request_id": str(request_id),
                            "event_kind": "aiperf_metric", "scope": "request",
                            "metric_name": metric_name, "value": value, "unit": unit,
                            "timestamp_unix_ns": timestamp_ns, "monotonic_ns": None,
                            "source_tool": "aiperf", "source_version": aiperf_version,
                            "source_schema_version": source_schema,
                            "source_file": records_rel, "source_record_index": line_number,
                            "metadata": {key: metadata.get(key) for key in REQUEST_METADATA_FIELDS if key in metadata},
                            "quality": "available" if value is not None else "unavailable",
                        }
                        write_event(stream, event)
                        event_count += 1
                        request_metric_count += 1

        if server_metrics_path is not None:
            server_metric_record_count, server_metric_sample_count = import_server_metrics(
                stream, server_metrics_path, server_metrics_rel, run_id, aiperf_version, source_schema)
            event_count += server_metric_sample_count
        if server_metrics_summary_path is not None:
            server_metric_aggregate_count = import_server_metrics_aggregate(
                stream, server_metrics_aggregate, server_metrics_summary_rel, run_id, aiperf_version)
            event_count += server_metric_aggregate_count
        if gpu_telemetry_path is not None:
            gpu_telemetry_record_count, gpu_telemetry_metric_count = import_gpu_telemetry(
                stream, gpu_telemetry_path, gpu_telemetry_rel, run_id, aiperf_version, source_schema)
            event_count += gpu_telemetry_metric_count

    os.replace(event_path.with_name(event_path.name + ".tmp"), event_path)
    if summary_path is None:
        warnings.append("summary JSON not present; run-level aggregate metrics were not imported")
    if records_path is None:
        warnings.append("per-request JSONL not present; request-level metrics were not imported")
    if not request_count:
        warnings.append("no per-request records were available")
    if server_metrics_path is None:
        warnings.append("server metrics JSONL not present; server time-series metrics were not imported")
    if server_metrics_summary_path is None:
        warnings.append("server metrics aggregate JSON not present; aggregate server metrics were not imported")
    if gpu_telemetry_path is None:
        warnings.append("GPU telemetry JSONL not present; GPU device metrics were not imported")
    report = {
        "schema_version": OUTPUT_SCHEMA,
        "status": "imported",
        "run_id": run_id,
        "source_tool": "aiperf",
        "aiperf_version": aiperf_version,
        "source_schema_version": source_schema,
        "source_artifacts": source_files,
        "summary_file": summary_rel,
        "records_file": records_rel,
        "server_metrics_file": server_metrics_rel,
        "server_metrics_summary_file": server_metrics_summary_rel,
        "gpu_telemetry_file": gpu_telemetry_rel,
        "server_metric_record_count": server_metric_record_count,
        "server_metric_sample_count": server_metric_sample_count,
        "server_metric_aggregate_count": server_metric_aggregate_count,
        "gpu_telemetry_record_count": gpu_telemetry_record_count,
        "gpu_telemetry_metric_count": gpu_telemetry_metric_count,
        "preserved_unparsed_phase_files": [path.relative_to(root).as_posix() for path in ignored_phase_summaries + ignored_phase_records + ignored_phase_server_summaries],
        "event_file": event_path.name,
        "event_count": event_count,
        "summary_metric_count": summary_metric_count,
        "request_count": request_count,
        "request_metric_count": request_metric_count,
        "failed_request_count": failed_request_count,
        "warnings": warnings,
        "privacy": {"prompts_imported": False, "generated_text_imported": False,
                    "credentials_imported": False, "raw_payloads_imported": False},
        "clock_policy": "AIPerf request epoch timestamps are preserved; monotonic_ns is null because no shared monotonic clock is provided.",
    }
    atomic_write(out / "aiperf_import_report.json", json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = import_aiperf(args.artifacts_dir, args.output_dir)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({key: report[key] for key in (
        "status", "run_id", "event_count", "summary_metric_count",
        "request_count", "request_metric_count", "failed_request_count",
        "server_metric_record_count", "server_metric_sample_count", "server_metric_aggregate_count",
        "gpu_telemetry_record_count", "gpu_telemetry_metric_count", "warnings",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())