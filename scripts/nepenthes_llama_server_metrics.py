#!/usr/bin/env python3
"""Offline parsers for llama-server Prometheus /metrics and JSON /slots snapshots.

Only bounded, non-sensitive slot fields and allowlisted metric labels are exported.
Unknown metric names remain intact; unknown label values and slot fields are not copied.
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
LABEL_ALLOWLIST = {"model", "status", "backend", "device", "device_id", "type", "operation", "slot_id", "result", "method"}
METRIC_RE = re.compile(r"^([a-zA-Z_:][a-zA-Z0-9_:]*)(?:\{(.*)\})?\s+(\S+)(?:\s+(\d+))?$")
NAME_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


def stable_id(*parts: Any) -> str:
    raw = "\0".join(str(part) for part in parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:32]


def parse_labels(raw: str | None) -> dict[str, str]:
    if not raw:
        return {}
    labels: dict[str, str] = {}
    pos = 0
    while pos < len(raw):
        match = NAME_RE.match(raw, pos)
        if not match:
            raise ValueError(f"invalid Prometheus label syntax at offset {pos}")
        name = match.group(0)
        pos = match.end()
        while pos < len(raw) and raw[pos].isspace():
            pos += 1
        if pos >= len(raw) or raw[pos] != '=':
            raise ValueError(f"expected '=' after label {name}")
        pos += 1
        while pos < len(raw) and raw[pos].isspace():
            pos += 1
        if pos >= len(raw) or raw[pos] != '"':
            raise ValueError(f"expected quoted value for label {name}")
        pos += 1
        chars: list[str] = []
        while pos < len(raw):
            ch = raw[pos]
            pos += 1
            if ch == '"':
                break
            if ch == '\\':
                if pos >= len(raw):
                    raise ValueError(f"unterminated escape in label {name}")
                escaped = raw[pos]
                pos += 1
                chars.append({'n': '\n', '\\': '\\', '"': '"'}.get(escaped, escaped))
            else:
                chars.append(ch)
        else:
            raise ValueError(f"unterminated value for label {name}")
        if name in labels:
            raise ValueError(f"duplicate Prometheus label: {name}")
        labels[name] = ''.join(chars)
        while pos < len(raw) and raw[pos].isspace():
            pos += 1
        if pos < len(raw):
            if raw[pos] != ',':
                raise ValueError(f"expected ',' after label {name}")
            pos += 1
            while pos < len(raw) and raw[pos].isspace():
                pos += 1
            if pos == len(raw):
                raise ValueError("trailing comma in Prometheus labels")
    return labels


def parse_number(raw: str) -> float:
    if raw in {"+Inf", "Inf"}:
        return math.inf
    if raw == "-Inf":
        return -math.inf
    if raw == "NaN":
        return math.nan
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid Prometheus sample value: {raw}") from exc


def parse_prometheus(text: str, *, scrape_timestamp_unix_ns: int | None = None, scrape_id: str = "scrape") -> list[dict[str, Any]]:
    help_text: dict[str, str] = {}
    metric_types: dict[str, str] = {}
    metric_units: dict[str, str] = {}
    events: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") and line != "# EOF":
            parts = line[1:].strip().split(None, 2)
            if len(parts) >= 2 and parts[0] in {"HELP", "TYPE", "UNIT"}:
                kind, name = parts[0], parts[1]
                value = parts[2] if len(parts) == 3 else ""
                if kind == "HELP":
                    help_text[name] = value
                elif kind == "TYPE":
                    metric_types[name] = value
                else:
                    metric_units[name] = value
            continue
        match = METRIC_RE.match(line)
        if not match:
            raise ValueError(f"invalid Prometheus exposition at line {line_number}")
        name, raw_labels, raw_value, raw_timestamp = match.groups()
        labels = parse_labels(raw_labels)
        value = parse_number(raw_value)
        safe_labels = {key: val for key, val in labels.items() if key in LABEL_ALLOWLIST}
        dropped = sorted(set(labels) - set(safe_labels))
        timestamp_ns = int(raw_timestamp) * 1_000_000 if raw_timestamp is not None else scrape_timestamp_unix_ns
        events.append({
            "schema_version": SCHEMA_VERSION,
            "event_id": stable_id(scrape_id, line_number, name, sorted(safe_labels.items()), raw_value, raw_timestamp),
            "event_kind": "llama_server_metric",
            "scope": "server_scrape",
            "metric_name": name,
            "metric_type": metric_types.get(name),
            "description": help_text.get(name),
            "value": value if math.isfinite(value) else None,
            "value_special": raw_value if not math.isfinite(value) else None,
            "unit": metric_units.get(name),
            "labels": safe_labels,
            "dropped_label_names": dropped,
            "timestamp_unix_ns": timestamp_ns,
            "monotonic_ns": None,
            "timestamp_source": "prometheus_sample" if raw_timestamp is not None else ("scrape_wall_clock" if scrape_timestamp_unix_ns is not None else "unknown"),
            "source_tool": "llama.cpp",
            "source_endpoint": "/metrics",
            "quality": "available",
        })
    return events


def parse_slots(payload: Any, *, timestamp_unix_ns: int | None = None, snapshot_id: str = "slots") -> list[dict[str, Any]]:
    if isinstance(payload, dict) and isinstance(payload.get("slots"), list):
        slots = payload["slots"]
    elif isinstance(payload, list):
        slots = payload
    else:
        raise ValueError("/slots snapshot must be a JSON array or an object with a slots array")
    events: list[dict[str, Any]] = []
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise ValueError(f"slot entry {index} must be a JSON object")
        slot_id = slot.get("id", slot.get("id_slot"))
        if slot_id is not None and not isinstance(slot_id, (str, int)):
            raise ValueError(f"slot id at index {index} must be a string or integer")
        is_processing = slot.get("is_processing")
        if is_processing is not None and not isinstance(is_processing, bool):
            raise ValueError(f"is_processing at slot {index} must be boolean")
        events.append({
            "schema_version": SCHEMA_VERSION,
            "event_id": stable_id(snapshot_id, index, slot_id, is_processing),
            "event_kind": "llama_server_slot_snapshot",
            "scope": "server_snapshot",
            "slot_index": index,
            "slot_id": str(slot_id) if slot_id is not None else None,
            "is_processing": is_processing,
            "timestamp_unix_ns": timestamp_unix_ns,
            "monotonic_ns": None,
            "source_tool": "llama.cpp",
            "source_endpoint": "/slots",
            "unsupported_field_names": sorted(set(slot) - {"id", "id_slot", "is_processing"}),
            "quality": "available" if slot_id is not None or is_processing is not None else "no_supported_fields",
        })
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics-file", type=Path)
    parser.add_argument("--slots-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scrape-timestamp-unix-ns", type=int)
    parser.add_argument("--snapshot-id", default="llama-server-snapshot")
    args = parser.parse_args()
    if not args.metrics_file and not args.slots_file:
        parser.error("provide --metrics-file and/or --slots-file")
    events: list[dict[str, Any]] = []
    try:
        if args.metrics_file:
            events.extend(parse_prometheus(args.metrics_file.read_text(encoding="utf-8"),
                                           scrape_timestamp_unix_ns=args.scrape_timestamp_unix_ns,
                                           scrape_id=args.snapshot_id))
        if args.slots_file:
            slots = json.loads(args.slots_file.read_text(encoding="utf-8"))
            events.extend(parse_slots(slots, timestamp_unix_ns=args.scrape_timestamp_unix_ns,
                                      snapshot_id=args.snapshot_id))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_name(args.output.name + ".tmp")
        with temporary.open("w", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
        os.replace(temporary, args.output)
        print(json.dumps({"event_count": len(events), "output": str(args.output)}, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())