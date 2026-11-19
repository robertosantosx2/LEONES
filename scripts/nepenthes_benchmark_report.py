#!/usr/bin/env python3
"""Build reproducible latency, throughput and energy reports from NEPENTHES events.

All percentiles use linear interpolation over sorted observations. Per-request
ITL values are request-level averages; the report never presents them as
individual token intervals unless the source actually supplies a vector.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
from pathlib import Path
from typing import Any

METRIC_NAMES = (
    "request_latency", "time_to_first_token", "inter_token_latency",
    "inter_chunk_latency", "output_token_count", "output_sequence_length",
)


def finite(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return float(value)


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def describe(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None,
                "stddev_population": None, "mad": None, "iqr": None, "cv": None,
                "p50": None, "p90": None, "p95": None, "p99": None}
    mean = statistics.fmean(values)
    median = statistics.median(values)
    deviations = [abs(value - median) for value in values]
    stddev = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {
        "count": len(values), "min": min(values), "max": max(values),
        "mean": mean, "median": median, "stddev_population": stddev,
        "mad": statistics.median(deviations),
        "iqr": (percentile(values, 0.75) or 0.0) - (percentile(values, 0.25) or 0.0),
        "cv": stddev / abs(mean) if mean != 0 else None,
        "p50": percentile(values, 0.50), "p90": percentile(values, 0.90),
        "p95": percentile(values, 0.95), "p99": percentile(values, 0.99),
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
                raise ValueError(f"invalid events JSONL at line {line_number}: {exc}") from exc
            if not isinstance(event, dict):
                raise ValueError(f"event at line {line_number} must be an object")
            events.append(event)
    return events


def metric_observations(events: list[dict[str, Any]], metric_name: str) -> tuple[list[float], str | None, int]:
    values: list[float] = []
    unit = None
    requests_with_metric = 0
    for event in events:
        if event.get("event_kind") != "aiperf_metric" or event.get("scope") != "request" or event.get("metric_name") != metric_name:
            continue
        unit = unit or event.get("unit")
        value = event.get("value")
        if isinstance(value, list):
            parsed = [number for item in value if (number := finite(item)) is not None]
            if parsed:
                values.extend(parsed)
                requests_with_metric += 1
        else:
            number = finite(value)
            if number is not None:
                values.append(number)
                requests_with_metric += 1
    return values, unit, requests_with_metric


def read_energy_summary(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read NVML energy summary {path}: {exc}") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("devices"), list):
        raise ValueError("NVML energy summary must contain a devices array")
    devices = {}
    for device in payload["devices"]:
        if not isinstance(device, dict) or not isinstance(device.get("gpu_uuid"), str):
            continue
        energy = device.get("energy") if isinstance(device.get("energy"), dict) else {}
        devices[device["gpu_uuid"]] = {
            "energy_j": finite(energy.get("energy_j")),
            "method": energy.get("method"), "quality": energy.get("quality"),
        }
    return {"duration_seconds": finite(payload.get("duration_seconds")), "devices": devices}


def energy_efficiency(run_path: Path | None, baseline_path: Path | None,
                      content_tokens: float | None, sequence_tokens: float | None) -> dict[str, Any]:
    if run_path is None:
        return {"status": "not_requested", "device_attribution": "device_level_not_process_level"}
    run = read_energy_summary(run_path)
    run_devices = run["devices"]
    allowed = {"measured_counter", "estimated"}
    run_valid = bool(run_devices) and all(
        item["energy_j"] is not None and item["quality"] in allowed for item in run_devices.values()
    )
    run_energy = sum(item["energy_j"] for item in run_devices.values() if item["energy_j"] is not None)
    result = {
        "status": "run_energy_available" if run_valid else "run_energy_incomplete",
        "run_energy_j": run_energy if run_valid else None,
        "run_duration_seconds": run["duration_seconds"],
        "run_devices": {key: value for key, value in run_devices.items()},
        "device_attribution": "device_level_not_process_level",
        "tokens_per_joule_content": None, "joules_per_content_token": None,
        "tokens_per_joule_sequence": None, "joules_per_sequence_token": None,
    }
    if baseline_path is None:
        result["status"] = "baseline_not_provided" if run_valid else "run_energy_incomplete"
        return result
    baseline = read_energy_summary(baseline_path)
    baseline_devices = baseline["devices"]
    same_devices = set(run_devices) == set(baseline_devices) and bool(run_devices)
    baseline_valid = same_devices and all(
        item["energy_j"] is not None and item["quality"] in allowed for item in baseline_devices.values()
    )
    run_duration = run["duration_seconds"]
    baseline_duration = baseline["duration_seconds"]
    if not run_valid or not baseline_valid or run_duration is None or baseline_duration is None or run_duration <= 0 or baseline_duration <= 0:
        result["status"] = "energy_or_baseline_incomplete"
        return result
    baseline_scaled = sum(
        baseline_devices[key]["energy_j"] * (run_duration / baseline_duration)
        for key in run_devices
    )
    incremental = run_energy - baseline_scaled
    result.update({
        "status": "available" if incremental > 0 else "invalid_nonpositive_incremental_energy",
        "baseline_energy_scaled_j": baseline_scaled,
        "incremental_energy_j": incremental if incremental > 0 else None,
        "baseline_duration_seconds": baseline_duration,
    })
    if incremental <= 0:
        return result
    if content_tokens is not None and content_tokens > 0:
        result["tokens_per_joule_content"] = content_tokens / incremental
        result["joules_per_content_token"] = incremental / content_tokens
    if sequence_tokens is not None and sequence_tokens > 0:
        result["tokens_per_joule_sequence"] = sequence_tokens / incremental
        result["joules_per_sequence_token"] = incremental / sequence_tokens
    return result


def build_report(events: list[dict[str, Any]], nvml_run: Path | None = None,
                 nvml_baseline: Path | None = None) -> dict[str, Any]:
    request_ids = {str(event.get("request_id")) for event in events
                   if event.get("scope") == "request" and event.get("request_id") is not None}
    failed_ids = {str(event.get("request_id")) for event in events
                  if event.get("event_kind") == "aiperf_request_error" and event.get("request_id") is not None}
    metric_report = {}
    for name in METRIC_NAMES:
        values, unit, request_count = metric_observations(events, name)
        metric_report[name] = {"unit": unit, "request_count_with_metric": request_count, **describe(values)}
    output_values, _, _ = metric_observations(events, "output_token_count")
    output_tokens = sum(output_values) if output_values else None
    sequence_values, _, _ = metric_observations(events, "output_sequence_length")
    sequence_tokens = sum(sequence_values) if sequence_values else None
    run_summary = {
        event.get("metric_name"): {"value": event.get("value"), "unit": event.get("unit"),
                                   "statistics": event.get("statistics", {})}
        for event in events if event.get("event_kind") == "aiperf_metric" and event.get("scope") == "run_summary"
    }
    output_tokens = output_tokens if output_tokens is not None else (
        finite(run_summary.get("total_output_tokens", {}).get("statistics", {}).get("sum"))
        if isinstance(run_summary.get("total_output_tokens"), dict) else None)
    sequence_tokens = sequence_tokens if sequence_tokens is not None else (
        finite(run_summary.get("total_output_sequence_length", {}).get("statistics", {}).get("sum"))
        if isinstance(run_summary.get("total_output_sequence_length"), dict) else None)
    energy = energy_efficiency(nvml_run, nvml_baseline, output_tokens, sequence_tokens)
    server_metric_events = [event for event in events if str(event.get("event_kind", "")).startswith("aiperf_server_metric") or event.get("event_kind") == "llama_server_metric"]
    gpu_metric_events = [event for event in events if event.get("event_kind") in {"aiperf_gpu_telemetry", "nvml_device_sample"}]
    return {
        "schema_version": "1.0", "event_count": len(events),
        "request_count": len(request_ids), "failed_request_count": len(failed_ids),
        "successful_request_count": max(0, len(request_ids - failed_ids)),
        "content_output_tokens": output_tokens,
        "completion_sequence_tokens": sequence_tokens,
        "request_metrics": metric_report, "run_summary_metrics": run_summary,
        "server_metric_event_count": len(server_metric_events),
        "gpu_telemetry_event_count": len(gpu_metric_events),
        "energy_efficiency": energy,
        "statistics_method": "population standard deviation; MAD about median; IQR=P75-P25; percentiles use linear interpolation at (n-1)*q.",
        "itl_interpretation": "AIPerf inter_token_latency is a per-request average unless the source event contains an explicit list; report count is request averages, not per-token samples.",
        "privacy": {"request_ids_in_report": False, "prompts_in_report": False, "generated_text_in_report": False, "credentials_in_report": False},
    }


def markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# NEPENTHES benchmark report",
        "",
        f"- Requests: {report['request_count']} ({report['successful_request_count']} successful, {report['failed_request_count']} failed)",
        f"- Content output tokens: {report['content_output_tokens']}",
        f"- Completion sequence tokens: {report['completion_sequence_tokens']}",
        f"- Server metric events: {report['server_metric_event_count']}",
        f"- GPU telemetry events: {report['gpu_telemetry_event_count']}",
        "",
        "## Request latency and token metrics",
        "",
        "| Metric | Unit | n | Mean | Median | Stddev | MAD | IQR | P95 | P99 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, stats in report["request_metrics"].items():
        lines.append("| {name} | {unit} | {count} | {mean} | {median} | {std} | {mad} | {iqr} | {p95} | {p99} |".format(
            name=name, unit=stats["unit"] or "—", count=stats["count"],
            mean=stats["mean"], median=stats["median"], std=stats["stddev_population"],
            mad=stats["mad"], iqr=stats["iqr"], p95=stats["p95"], p99=stats["p99"]))
    energy = report["energy_efficiency"]
    lines.extend(["", "## Energy", "", f"- Status: {energy['status']}",
                  f"- Run energy (device-level): {energy.get('run_energy_j')}",
                  f"- Baseline-adjusted incremental energy: {energy.get('incremental_energy_j')}",
                  f"- Content tokens/J: {energy.get('tokens_per_joule_content')}",
                  f"- Completion tokens/J: {energy.get('tokens_per_joule_sequence')}",
                  "", "> NVML energy is device-wide and must not be interpreted as process-attributed.",
                  "", "## Method", "", report["statistics_method"], "", report["itl_interpretation"], ""])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--nvml-run-summary", type=Path)
    parser.add_argument("--nvml-baseline-summary", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = build_report(load_events(args.events), args.nvml_run_summary, args.nvml_baseline_summary)
        output = args.output_dir.expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        json_path = output / "nepenthes-benchmark-report.json"
        md_path = output / "nepenthes-benchmark-report.md"
        for path in (json_path, md_path):
            if path.exists():
                raise ValueError(f"report output already exists: {path}")
        json_tmp = json_path.with_name(json_path.name + ".tmp")
        md_tmp = md_path.with_name(md_path.name + ".tmp")
        json_tmp.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        md_tmp.write_text(markdown_report(report), encoding="utf-8")
        os.replace(json_tmp, json_path)
        os.replace(md_tmp, md_path)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"request_count": report["request_count"],
                      "failed_request_count": report["failed_request_count"],
                      "energy_status": report["energy_efficiency"]["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())