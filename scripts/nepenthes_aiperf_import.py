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
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

OUTPUT_SCHEMA = "1.0"
SUMMARY_NAMES = ("profile_export_aiperf.json",)
RECORD_NAMES = ("profile_export.jsonl",)
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
    if len(matches) > 1:
        raise ValueError(f"multiple candidate artifacts found for {names}: "
                         + ", ".join(str(path) for path in matches))
    return matches[0] if matches else None


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

    summary_path = discover_one(root, SUMMARY_NAMES)
    records_path = discover_one(root, RECORD_NAMES)
    if summary_path is None and records_path is None:
        raise ValueError("no supported AIPerf artifacts found (summary JSON or records JSONL)")

    summary: dict[str, Any] = {}
    if summary_path is not None:
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read AIPerf summary {summary_path}: {exc}") from exc
        if not isinstance(summary, dict):
            raise ValueError("AIPerf summary root must be a JSON object")

    source_files = inventory(root)
    run_info = summary.get("run_info") if isinstance(summary.get("run_info"), dict) else {}
    run_id = str(summary.get("benchmark_id") or run_info.get("benchmark_id") or
                 stable_id("aiperf-run", *(item["sha256"] for item in source_files)))
    aiperf_version = summary.get("aiperf_version")
    source_schema = summary.get("schema_version")
    summary_rel = summary_path.relative_to(root).as_posix() if summary_path else None
    records_rel = records_path.relative_to(root).as_posix() if records_path else None
    summary_timestamp = parse_timestamp_ns(summary.get("start_time"))
    event_path = out / "aiperf_events.jsonl"
    event_count = 0
    summary_metric_count = 0
    request_metric_count = 0
    request_count = 0
    failed_request_count = 0
    warnings: list[str] = []

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

    os.replace(event_path.with_name(event_path.name + ".tmp"), event_path)
    if summary_path is None:
        warnings.append("summary JSON not present; run-level aggregate metrics were not imported")
    if records_path is None:
        warnings.append("per-request JSONL not present; request-level metrics were not imported")
    if not request_count:
        warnings.append("no per-request records were available")
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
        "request_count", "request_metric_count", "failed_request_count", "warnings",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())