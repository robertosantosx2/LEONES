from __future__ import annotations

import json
from urllib.error import HTTPError

import pytest

from scripts.nepenthes_llama_server_capture import capture, validate_server_url


class FakeResponse:
    def __init__(self, body: bytes, status: int = 200):
        self.body = body
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.body


def test_capture_collects_metrics_and_safe_slots_without_persisting_raw_payloads(tmp_path):
    metrics = b'llama_requests_total{model="qwen-local",request_id="private-id"} 3\\n'
    slots = json.dumps([{
        "id": 1, "is_processing": True, "prompt": "private prompt text",
        "next_token": "private token",
    }]).encode()
    calls = []
    def opener(request, timeout):
        calls.append(request.full_url)
        return FakeResponse(metrics if request.full_url.endswith("/metrics") else slots)
    mono = iter([0, 100, 1_000_000_000, 1_000_000_100])
    wall = iter([1000, 2000, 3000])
    manifest = capture(
        url="http://127.0.0.1:8080", output_dir=tmp_path / "capture",
        duration_seconds=1.0, interval_ms=1000, timeout_seconds=1.0,
        run_id="capture-1", opener=opener,
        monotonic_clock_ns=lambda: next(mono), wall_clock_ns=lambda: next(wall),
        sleeper=lambda _: None,
    )
    assert calls == ["http://127.0.0.1:8080/metrics", "http://127.0.0.1:8080/slots"]
    assert manifest["metrics_scrape_count"] == 1
    assert manifest["slots_snapshot_count"] == 1
    assert manifest["event_count"] == 2
    assert manifest["raw_payloads_persisted"] is False
    assert len(manifest["source_snapshots"]) == 2
    events_path = tmp_path / "capture" / "llama_server_events.jsonl"
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    metric = next(event for event in events if event["event_kind"] == "llama_server_metric")
    slot = next(event for event in events if event["event_kind"] == "llama_server_slot_snapshot")
    assert metric["labels"] == {"model": "qwen-local"}
    assert metric["dropped_label_names"] == ["request_id"]
    assert slot["slot_id"] == "1" and slot["is_processing"] is True
    assert slot["unsupported_field_names"] == ["next_token", "prompt"]
    serialized = json.dumps(events) + json.dumps(manifest)
    assert "private prompt text" not in serialized
    assert "private token" not in serialized
    assert "private-id" not in serialized
    assert not (tmp_path / "capture" / "raw").exists()


def test_capture_tolerates_metrics_disabled_unless_required(tmp_path):
    slots = b'[{"id":0,"is_processing":false}]'
    def opener(request, timeout):
        if request.full_url.endswith("/metrics"):
            raise HTTPError(request.full_url, 404, "not found", {}, None)
        return FakeResponse(slots)
    mono = iter([0, 100, 1_000_000_000, 1_000_000_100])
    wall = iter([1000, 2000, 3000])
    manifest = capture(url="http://localhost:8080", output_dir=tmp_path / "optional",
                       duration_seconds=1, interval_ms=1000, opener=opener,
                       monotonic_clock_ns=lambda: next(mono), wall_clock_ns=lambda: next(wall),
                       sleeper=lambda _: None)
    assert manifest["metrics_enabled"] is False
    assert manifest["slots_available"] is True
    assert any("start llama-server with --metrics" in warning for warning in manifest["warnings"])


def test_capture_fails_when_metrics_are_required_but_endpoint_is_disabled(tmp_path):
    def opener(request, timeout):
        raise HTTPError(request.full_url, 404, "not found", {}, None)
    with pytest.raises(RuntimeError, match="--require-metrics was specified"):
        capture(url="http://127.0.0.1:8080", output_dir=tmp_path / "required",
                duration_seconds=1, interval_ms=1000, require_metrics=True, opener=opener)


def test_capture_rejects_remote_plain_http_and_nonempty_output(tmp_path):
    with pytest.raises(ValueError, match="must use HTTPS"):
        validate_server_url("http://server.example:8080")
    output = tmp_path / "not-empty"
    output.mkdir()
    (output / "keep.txt").write_text("keep")
    with pytest.raises(ValueError, match="not empty"):
        capture(url="http://127.0.0.1:8080", output_dir=output)


def test_capture_rejects_invalid_slots_json(tmp_path):
    def opener(request, timeout):
        return FakeResponse(b"not-json" if request.full_url.endswith("/slots") else b"")
    mono = iter([0, 100])
    wall = iter([1000, 2000])
    with pytest.raises(ValueError, match="invalid /slots JSON"):
        capture(url="http://127.0.0.1:8080", output_dir=tmp_path / "bad-slots",
                duration_seconds=1, interval_ms=1000, opener=opener,
                monotonic_clock_ns=lambda: next(mono), wall_clock_ns=lambda: next(wall))