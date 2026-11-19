"""Shared, fail-closed NEPENTHES trace-envelope validation.

Connector profiles are explicit. Adding a source requires a reviewed profile here;
callers cannot register arbitrary source names at runtime.
"""
from __future__ import annotations

from typing import Any

UINT64_MAX = 0xFFFFFFFFFFFFFFFF
ATTRIBUTION_LEVELS = frozenset({"exact", "windowed", "device_wide", "estimated"})
FORBIDDEN_FIELDS = frozenset({
    "prompt", "completion", "response", "text", "tokens", "token_ids",
    "input_text", "output_text",
})
EVENT_FIELDS = frozenset({
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "monotonic_ns", "request_id", "event_kind", "label", "value0", "value1",
    "duration_ns", "flags",
})
OPTIONAL_EVENT_FIELDS = frozenset({"correlation_token", "attribution_level", "clock_domain"})
SUMMARY_FIELDS = frozenset({
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "event_kind", "events_drained", "dropped_events", "write_errors",
})

# Both accepted connectors currently emit host monotonic timestamps in steady_clock.
# Keep this per-source so future engines must declare their own supported domain.
SOURCE_PROFILES: dict[str, dict[str, frozenset[str]]] = {
    "llama.cpp": {"clock_domains": frozenset({"steady_clock"})},
    "tensorfold": {"clock_domains": frozenset({"steady_clock"})},
}


def require_uint(
    record: dict[str, Any],
    field: str,
    line_no: int,
    maximum: int = UINT64_MAX,
) -> int:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"line {line_no}: {field} must be a non-negative integer")
    if value > maximum:
        raise ValueError(f"line {line_no}: {field} exceeds {maximum}")
    return value


def _validate_source(record: dict[str, Any], line_no: int, expected_source: str) -> None:
    if expected_source not in SOURCE_PROFILES:
        raise ValueError(f"unregistered trace source: {expected_source}")
    if record.get("source") != expected_source:
        raise ValueError(f"line {line_no}: source must be {expected_source}")


def validate_event_envelope(
    record: dict[str, Any], line_no: int, expected_source: str
) -> None:
    """Validate common fields and source-profile rules for one event."""
    _validate_source(record, line_no, expected_source)
    missing = EVENT_FIELDS - record.keys()
    extra = record.keys() - EVENT_FIELDS - OPTIONAL_EVENT_FIELDS
    if missing:
        raise ValueError(f"line {line_no}: event missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"line {line_no}: unexpected event fields: {sorted(extra)}")
    if record.get("schema_version") != "1.0":
        raise ValueError(f"line {line_no}: unsupported schema_version")
    if not isinstance(record.get("run_id"), str) or not record["run_id"]:
        raise ValueError(f"line {line_no}: invalid run_id")
    if not isinstance(record.get("event_id"), str) or not record["event_id"]:
        raise ValueError(f"line {line_no}: invalid event_id")

    for field in (
        "timestamp_unix_ns", "monotonic_ns", "request_id",
        "value0", "value1", "duration_ns",
    ):
        require_uint(record, field, line_no)
    require_uint(record, "flags", line_no, maximum=65535)

    token = record.get("correlation_token")
    if token is not None:
        if isinstance(token, bool) or not isinstance(token, int) or not 0 < token <= UINT64_MAX:
            raise ValueError(
                f"line {line_no}: correlation_token must be null or a positive unsigned 64-bit integer"
            )
    attribution = record.get("attribution_level")
    if attribution is not None and (not isinstance(attribution, str) or attribution not in ATTRIBUTION_LEVELS):
        raise ValueError(f"line {line_no}: invalid attribution_level")
    if attribution == "exact" and token is None:
        raise ValueError(f"line {line_no}: exact attribution requires correlation_token")
    if token is not None and attribution != "exact":
        raise ValueError(f"line {line_no}: correlation_token requires exact attribution_level")

    clock_domain = record.get("clock_domain")
    if clock_domain is not None and (
        not isinstance(clock_domain, str)
        or clock_domain not in SOURCE_PROFILES[expected_source]["clock_domains"]
    ):
        if expected_source == "llama.cpp":
            raise ValueError(f"line {line_no}: unsupported llama.cpp clock_domain")
        raise ValueError(f"line {line_no}: unsupported {expected_source} clock_domain")
    if not isinstance(record.get("event_kind"), str) or not record["event_kind"]:
        raise ValueError(f"line {line_no}: invalid event_kind")
    if not isinstance(record.get("label"), str):
        raise ValueError(f"line {line_no}: label must be a string")


def validate_summary_envelope(
    record: dict[str, Any], line_no: int, expected_source: str
) -> None:
    """Validate the final sink accounting record for a registered connector."""
    missing = SUMMARY_FIELDS - record.keys()
    extra = record.keys() - SUMMARY_FIELDS
    if missing:
        raise ValueError(f"line {line_no}: sink summary missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"line {line_no}: unexpected sink summary fields: {sorted(extra)}")
    if record.get("schema_version") != "1.0":
        raise ValueError(f"line {line_no}: unsupported sink summary schema/source")
    _validate_source(record, line_no, expected_source)
    if record.get("event_kind") != "sink_summary":
        raise ValueError(f"line {line_no}: invalid sink summary event_kind")
    if not isinstance(record.get("run_id"), str) or not record["run_id"]:
        raise ValueError(f"line {line_no}: invalid summary run_id")
    if not isinstance(record.get("event_id"), str) or not record["event_id"]:
        raise ValueError(f"line {line_no}: invalid summary event_id")
    for field in ("timestamp_unix_ns", "events_drained", "dropped_events", "write_errors"):
        require_uint(record, field, line_no)
