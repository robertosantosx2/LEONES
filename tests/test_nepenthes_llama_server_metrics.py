from __future__ import annotations

import json

import pytest

from scripts.nepenthes_llama_server_metrics import parse_prometheus, parse_slots


def test_prometheus_parser_keeps_types_units_and_sample_timestamps():
    payload = '''# HELP llama_prompt_tokens_total Number of prompt tokens processed.
# TYPE llama_prompt_tokens_total counter
# UNIT llama_prompt_tokens_total tokens
llama_prompt_tokens_total{model="local",status="ok"} 123 1795071000123
'''
    events = parse_prometheus(payload, scrape_timestamp_unix_ns=1234, scrape_id="run-1")
    assert len(events) == 1
    event = events[0]
    assert event["metric_name"] == "llama_prompt_tokens_total"
    assert event["metric_type"] == "counter"
    assert event["description"] == "Number of prompt tokens processed."
    assert event["unit"] == "tokens"
    assert event["value"] == 123
    assert event["labels"] == {"model": "local", "status": "ok"}
    assert event["timestamp_unix_ns"] == 1_795_071_000_123_000_000
    assert event["timestamp_source"] == "prometheus_sample"


def test_prometheus_parser_drops_unbounded_or_sensitive_label_values():
    events = parse_prometheus('llama_requests_total{model="m",request_id="secret-id",user="alice",status="ok"} 2')
    assert events[0]["labels"] == {"model": "m", "status": "ok"}
    assert events[0]["dropped_label_names"] == ["request_id", "user"]
    assert "secret-id" not in json.dumps(events)
    assert "alice" not in json.dumps(events)


def test_prometheus_parser_handles_escaped_label_values():
    events = parse_prometheus('llama_build_info{model="a\\\"b",backend="cuda\\nsm86"} 1')
    assert events[0]["labels"]["model"] == 'a"b'
    assert events[0]["labels"]["backend"] == "cuda\nsm86"


def test_prometheus_parser_preserves_histogram_samples_without_aggregating():
    payload = '''# TYPE request_duration_seconds histogram
request_duration_seconds_bucket{le="0.5"} 4
request_duration_seconds_bucket{le="+Inf"} 5
request_duration_seconds_sum 1.25
request_duration_seconds_count 5
'''
    events = parse_prometheus(payload)
    assert [e["metric_name"] for e in events] == [
        "request_duration_seconds_bucket", "request_duration_seconds_bucket",
        "request_duration_seconds_sum", "request_duration_seconds_count",
    ]
    assert events[1]["labels"] == {}
    assert events[1]["dropped_label_names"] == ["le"]


def test_prometheus_parser_represents_special_float_without_invalid_json():
    event = parse_prometheus('llama_value  NaN')[0]
    assert event["value"] is None
    assert event["value_special"] == "NaN"
    assert json.dumps(event, allow_nan=False)


def test_prometheus_parser_rejects_malformed_samples():
    with pytest.raises(ValueError, match="invalid Prometheus exposition"):
        parse_prometheus('this is not a metric sample')


def test_slots_parser_exports_only_safe_fields_and_never_prompt_values():
    payload = [{
        "id": 2, "is_processing": True,
        "prompt": "private prompt", "next_token": "private token",
    }]
    events = parse_slots(payload, timestamp_unix_ns=99, snapshot_id="slots-1")
    assert events[0]["slot_id"] == "2"
    assert events[0]["is_processing"] is True
    assert events[0]["unsupported_field_names"] == ["next_token", "prompt"]
    assert "private prompt" not in json.dumps(events)
    assert "private token" not in json.dumps(events)
    assert events[0]["timestamp_unix_ns"] == 99


def test_slots_parser_accepts_documented_list_or_wrapped_slots_shape():
    assert parse_slots({"slots": [{"id": 0, "is_processing": False}]})[0]["slot_id"] == "0"


def test_slots_parser_rejects_unknown_root_shape_and_invalid_boolean():
    with pytest.raises(ValueError, match="JSON array"):
        parse_slots({"data": []})
    with pytest.raises(ValueError, match="must be boolean"):
        parse_slots([{"id": 0, "is_processing": 1}])