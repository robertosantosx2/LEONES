"""Closed source registry and shared NEPENTHES JSONL envelope validation."""
from __future__ import annotations

from typing import Any

EVENT_FIELDS = {
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "monotonic_ns", "request_id", "event_kind", "label", "value0", "value1",
    "duration_ns", "flags",
}
OPTIONAL_EVENT_FIELDS = {"correlation_token", "attribution_level", "clock_domain"}
SUMMARY_FIELDS = {
    "schema_version", "run_id", "event_id", "source", "timestamp_unix_ns",
    "event_kind", "events_drained", "dropped_events", "write_errors",
}
FORBIDDEN_FIELDS = {
    "prompt", "completion", "response", "text", "tokens", "token_ids",
    "input_text", "output_text",
}
ATTRIBUTION_LEVELS = {"exact", "windowed", "device_wide", "estimated"}
UINT64_MAX = 0xFFFFFFFFFFFFFFFF

# This registry is intentionally closed. Add a connector only with a reviewed
# contract and fixtures; never treat an arbitrary source string as registered.
SOURCE_PROFILES = {
    "llama.cpp": {"clock_domains": frozenset({"steady_clock"})},
    "tensorfold": {"clock_domains": frozenset({"steady_clock"}), "request_lifecycle_requires_id": True},
    "tandem.cpp": {"clock_domains": frozenset({"steady_clock"})},
}


def source_profile(source: str) -> dict[str, Any]:
    profile = SOURCE_PROFILES.get(source)
    if profile is None:
        raise ValueError(f"unregistered NEPENTHES source: {source!r}")
    return profile


def require_uint(record: dict[str, Any], field: str, line_no: int,
          maximum: int = UINT64_MAX) -> int:
    value = record.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"line {line_no}: {field} must be a non-negative integer")
    if value > maximum:
        raise ValueError(f"line {line_no}: {field} exceeds {maximum}")
    return value


def validate_envelope_record(record: dict[str, Any], line_no: int,
                             expected_source: str) -> None:
    """Validate one common event or sink_summary envelope against a connector."""
    profile = source_profile(expected_source)
    forbidden = FORBIDDEN_FIELDS.intersection(record)
    if forbidden:
        raise ValueError(
            f"line {line_no}: trace contains forbidden text/token fields: {sorted(forbidden)}"
        )
    kind = record.get("event_kind")
    if kind == "sink_summary":
        missing = SUMMARY_FIELDS - record.keys()
        extra = record.keys() - SUMMARY_FIELDS
        if missing:
            raise ValueError(f"line {line_no}: sink summary missing fields: {sorted(missing)}")
        if extra:
            raise ValueError(f"line {line_no}: unexpected sink summary fields: {sorted(extra)}")
        if record.get("schema_version") != "1.0":
            raise ValueError(f"line {line_no}: unsupported sink summary schema/source")
        if record.get("source") != expected_source:
            raise ValueError(f"line {line_no}: sink summary source mismatch")
        if not isinstance(record.get("run_id"), str) or not record["run_id"]:
            raise ValueError(f"line {line_no}: invalid summary run_id")
        if not isinstance(record.get("event_id"), str) or not record["event_id"]:
            raise ValueError(f"line {line_no}: invalid summary event_id")
        require_uint(record, "timestamp_unix_ns", line_no)
        for field in ("events_drained", "dropped_events", "write_errors"):
            require_uint(record, field, line_no)
        return

    missing = EVENT_FIELDS - record.keys()
    extra = record.keys() - EVENT_FIELDS - OPTIONAL_EVENT_FIELDS
    if missing:
        raise ValueError(f"line {line_no}: event missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"line {line_no}: unexpected event fields: {sorted(extra)}")
    if record.get("schema_version") != "1.0":
        raise ValueError(f"line {line_no}: unsupported schema_version")
    if record.get("source") != expected_source:
        raise ValueError(f"line {line_no}: event source mismatch")
    if not isinstance(record.get("run_id"), str) or not record["run_id"]:
        raise ValueError(f"line {line_no}: invalid run_id")
    if not isinstance(record.get("event_id"), str) or not record["event_id"]:
        raise ValueError(f"line {line_no}: invalid event_id")
    if not isinstance(kind, str) or not kind:
        raise ValueError(f"line {line_no}: invalid event_kind")
    if not isinstance(record.get("label"), str):
        raise ValueError(f"line {line_no}: label must be a string")

    for field in ("timestamp_unix_ns", "monotonic_ns", "request_id",
                  "value0", "value1", "duration_ns"):
        require_uint(record, field, line_no)
    require_uint(record, "flags", line_no, maximum=65535)
    if profile.get("request_lifecycle_requires_id") and kind in {
        "request_start", "request_end", "request_error", "request_cancel"
    } and record["request_id"] == 0:
        raise ValueError(f"line {line_no}: {expected_source} request lifecycle events require a non-zero request_id")

    token = record.get("correlation_token")
    if token is not None:
        if isinstance(token, bool) or not isinstance(token, int) or not 0 < token <= UINT64_MAX:
            raise ValueError(
                f"line {line_no}: correlation_token must be null or a positive unsigned 64-bit integer"
            )
    attribution = record.get("attribution_level")
    if attribution is not None and attribution not in ATTRIBUTION_LEVELS:
        raise ValueError(f"line {line_no}: invalid attribution_level")
    if attribution == "exact" and token is None:
        raise ValueError(f"line {line_no}: exact attribution requires correlation_token")
    if token is not None and attribution != "exact":
        raise ValueError(f"line {line_no}: correlation_token requires exact attribution_level")

    clock_domain = record.get("clock_domain")
    if clock_domain is not None and clock_domain not in profile["clock_domains"]:
        raise ValueError(f"line {line_no}: unsupported {expected_source} clock_domain")
    if kind == "clock_calibration":
        if record["timestamp_unix_ns"] == 0:
            raise ValueError(f"line {line_no}: clock_calibration requires timestamp_unix_ns")
        if clock_domain not in profile["clock_domains"]:
            raise ValueError(
                f"line {line_no}: clock_calibration requires a supported {expected_source} clock_domain"
            )
