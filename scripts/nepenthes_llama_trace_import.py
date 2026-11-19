#!/usr/bin/env python3
"""Import and validate the NEPENTHES llama.cpp JSONL runtime trace."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any


EVENT_FIELDS = {
    "schema_version",
    "run_id",
    "event_id",
    "source",
    "timestamp_unix_ns",
    "monotonic_ns",
    "request_id",
    "event_kind",
    "label",
    "value0",
    "value1",
    "duration_ns",
    "flags",
}
SUMMARY_FIELDS = {
    "schema_version",
    "run_id",
    "event_id",
    "source",
    "timestamp_unix_ns",
    "event_kind",
    "events_drained",
    "dropped_events",
    "write_errors",
}


def _require_int(record: dict[str, Any], field: str, line_no: int, maximum: int | None = None) -> int:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"line {line_no}: {field} must be a non-negative integer")
    if maximum is not None and value > maximum:
        raise ValueError(f"line {line_no}: {field} exceeds {maximum}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_trace(input_path: Path, allow_incomplete: bool = False) -> dict[str, Any]:
    if not input_path.is_file():
        raise ValueError(f"input file does not exist: {input_path}")

    event_count = 0
    run_id: str | None = None
    event_ids: set[str] = set()
    kind_counts: collections.Counter[str] = collections.Counter()
    label_counts: collections.Counter[str] = collections.Counter()
    duration_stats: dict[str, dict[str, int]] = {}
    request_starts: collections.Counter[int] = collections.Counter()
    request_ends: collections.Counter[int] = collections.Counter()
    internal_events = 0
    min_monotonic_ns: int | None = None
    max_monotonic_ns: int | None = None
    summary: dict[str, Any] | None = None

    with input_path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                raise ValueError(f"line {line_no}: blank lines are not valid JSONL records")
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"line {line_no}: invalid JSON: {exc.msg}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"line {line_no}: record must be a JSON object")

            event_kind = record.get("event_kind")
            if event_kind == "sink_summary":
                if summary is not None:
                    raise ValueError(f"line {line_no}: duplicate sink_summary record")
                missing = SUMMARY_FIELDS - record.keys()
                if missing:
                    raise ValueError(f"line {line_no}: sink summary missing fields: {sorted(missing)}")
                if record.get("schema_version") != "1.0" or record.get("source") != "llama.cpp":
                    raise ValueError(f"line {line_no}: unsupported sink summary schema/source")
                summary_run = record.get("run_id")
                if not isinstance(summary_run, str) or not summary_run:
                    raise ValueError(f"line {line_no}: invalid summary run_id")
                if run_id is not None and summary_run != run_id:
                    raise ValueError(f"line {line_no}: summary run_id does not match events")
                run_id = summary_run
                summary = record
                _require_int(record, "timestamp_unix_ns", line_no)
                _require_int(record, "events_drained", line_no)
                _require_int(record, "dropped_events", line_no)
                _require_int(record, "write_errors", line_no)
                if not isinstance(record.get("event_id"), str) or not record["event_id"]:
                    raise ValueError(f"line {line_no}: invalid summary event_id")
                if record["event_id"] in event_ids:
                    raise ValueError(f"line {line_no}: duplicate event_id")
                event_ids.add(record["event_id"])
                if any(item.strip() for item in stream):
                    raise ValueError("sink_summary must be the final JSONL record")
                break

            if summary is not None:
                raise ValueError(f"line {line_no}: event found after sink_summary")
            missing = EVENT_FIELDS - record.keys()
            if missing:
                raise ValueError(f"line {line_no}: event missing fields: {sorted(missing)}")
            if record.get("schema_version") != "1.0":
                raise ValueError(f"line {line_no}: unsupported schema_version")
            if record.get("source") != "llama.cpp":
                raise ValueError(f"line {line_no}: source must be llama.cpp")
            current_run = record.get("run_id")
            if not isinstance(current_run, str) or not current_run:
                raise ValueError(f"line {line_no}: invalid run_id")
            if run_id is None:
                run_id = current_run
            elif current_run != run_id:
                raise ValueError(f"line {line_no}: mixed run_id values in one file")

            event_id = record.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                raise ValueError(f"line {line_no}: invalid event_id")
            if event_id in event_ids:
                raise ValueError(f"line {line_no}: duplicate event_id {event_id}")
            event_ids.add(event_id)

            _require_int(record, "timestamp_unix_ns", line_no)
            monotonic_ns = _require_int(record, "monotonic_ns", line_no)
            request_id = _require_int(record, "request_id", line_no)
            _require_int(record, "value0", line_no)
            _require_int(record, "value1", line_no)
            duration_ns = _require_int(record, "duration_ns", line_no)
            _require_int(record, "flags", line_no, maximum=65535)
            if not isinstance(event_kind, str) or not event_kind:
                raise ValueError(f"line {line_no}: invalid event_kind")
            label = record.get("label")
            if not isinstance(label, str):
                raise ValueError(f"line {line_no}: label must be a string")

            event_count += 1
            kind_counts[event_kind] += 1
            label_counts[label] += 1
            if request_id == 0:
                internal_events += 1
            if event_kind == "request_start" and request_id:
                request_starts[request_id] += 1
            elif event_kind == "request_end" and request_id:
                request_ends[request_id] += 1
            min_monotonic_ns = monotonic_ns if min_monotonic_ns is None else min(min_monotonic_ns, monotonic_ns)
            max_monotonic_ns = monotonic_ns if max_monotonic_ns is None else max(max_monotonic_ns, monotonic_ns)

            if duration_ns:
                stats = duration_stats.setdefault(event_kind, {"count": 0, "min_ns": duration_ns,
                                                               "max_ns": duration_ns, "sum_ns": 0})
                stats["count"] += 1
                stats["min_ns"] = min(stats["min_ns"], duration_ns)
                stats["max_ns"] = max(stats["max_ns"], duration_ns)
                stats["sum_ns"] += duration_ns

    if summary is None and not allow_incomplete:
        raise ValueError("missing final sink_summary; use --allow-incomplete only for interrupted captures")
    if run_id is None:
        raise ValueError("trace contains no events and no sink_summary")

    summary_present = summary is not None
    events_drained = summary.get("events_drained") if summary else None
    dropped_events = summary.get("dropped_events") if summary else None
    write_errors = summary.get("write_errors") if summary else None
    drained_matches = summary_present and events_drained == event_count
    no_loss = summary_present and dropped_events == 0 and write_errors == 0 and drained_matches

    for stats in duration_stats.values():
        stats["mean_ns"] = stats["sum_ns"] // stats["count"]

    unmatched_starts = sum(max(0, count - request_ends[request_id])
                           for request_id, count in request_starts.items())
    unmatched_ends = sum(max(0, count - request_starts[request_id])
                         for request_id, count in request_ends.items())

    return {
        "schema_version": "1.0",
        "source": "llama.cpp",
        "run_id": run_id,
        "input_file": input_path.name,
        "input_bytes": input_path.stat().st_size,
        "input_sha256": _sha256(input_path),
        "event_count": event_count,
        "event_kind_counts": dict(sorted(kind_counts.items())),
        "event_label_counts": dict(sorted(label_counts.items())),
        "duration_by_event_kind": dict(sorted(duration_stats.items())),
        "request_lifecycle": {
            "request_start_events": sum(request_starts.values()),
            "request_end_events": sum(request_ends.values()),
            "unmatched_request_starts": unmatched_starts,
            "unmatched_request_ends": unmatched_ends,
            "internal_events_request_id_zero": internal_events,
        },
        "monotonic_range_ns": {
            "min": min_monotonic_ns,
            "max": max_monotonic_ns,
        },
        "sink_summary": {
            "present": summary_present,
            "events_drained": events_drained,
            "dropped_events": dropped_events,
            "write_errors": write_errors,
            "drained_matches_event_count": drained_matches,
        },
        "capture_complete": bool(no_loss),
        "quality": {
            "summary_missing": not summary_present,
            "queue_dropped_events": dropped_events,
            "writer_errors": write_errors,
            "drained_count_mismatch": summary_present and not drained_matches,
            "request_lifecycle_unmatched": unmatched_starts + unmatched_ends,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="llama.cpp NEPENTHES JSONL trace")
    parser.add_argument("--output", type=Path, required=True, help="summary JSON output path")
    parser.add_argument("--allow-incomplete", action="store_true",
                        help="import an interrupted trace without a final sink_summary")
    args = parser.parse_args(argv)

    try:
        result = import_trace(args.input, allow_incomplete=args.allow_incomplete)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(args.output.name + ".tmp")
        temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, args.output)
    except (OSError, ValueError) as exc:
        print(f"nepenthes-llama-trace-import: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({
        "run_id": result["run_id"],
        "event_count": result["event_count"],
        "capture_complete": result["capture_complete"],
        "output": str(args.output),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
