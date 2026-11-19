from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from scripts.nepenthes_otel_transport import post_payload, send_directory, validate_endpoint


class FakeResponse:
    def __init__(self, status=200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b"{}"


def test_endpoint_requires_https_for_remote_and_rejects_embedded_secrets():
    assert validate_endpoint("http://127.0.0.1:4318") == "http://127.0.0.1:4318"
    assert validate_endpoint("https://collector.example:4318/base") == "https://collector.example:4318/base"
    with pytest.raises(ValueError, match="must use HTTPS"):
        validate_endpoint("http://collector.example:4318")
    with pytest.raises(ValueError, match="must not embed credentials"):
        validate_endpoint("https://user:pass@collector.example:4318")
    with pytest.raises(ValueError, match="must not embed credentials"):
        validate_endpoint("https://collector.example:4318?token=secret")


def test_post_payload_retries_retryable_http_errors_and_uses_auth_header():
    calls = []
    sleeps = []
    def opener(request, timeout):
        calls.append((request, timeout))
        if len(calls) == 1:
            raise HTTPError(request.full_url, 503, "unavailable", {}, None)
        return FakeResponse(200)
    result = post_payload("https://collector.example/v1/traces", {"resourceSpans": []},
                          auth_header="Bearer top-secret", timeout_seconds=4,
                          max_retries=2, backoff_seconds=0.25, opener=opener, sleeper=sleeps.append)
    assert result == {"status": "success", "http_status": 200, "attempts": 2}
    assert len(calls) == 2 and sleeps == [0.25]
    assert calls[0][0].get_header("Authorization") == "Bearer top-secret"
    assert calls[0][0].get_header("Content-type") == "application/json"
    assert json.loads(calls[0][0].data) == {"resourceSpans": []}


def test_post_payload_does_not_retry_non_retryable_4xx():
    calls = []
    def opener(request, timeout):
        calls.append(request)
        raise HTTPError(request.full_url, 400, "bad request", {}, None)
    with pytest.raises(RuntimeError, match="HTTP 400"):
        post_payload("https://collector.example/v1/metrics", {}, opener=opener,
                     max_retries=4, sleeper=lambda _: None)
    assert len(calls) == 1


def test_post_payload_retries_transport_errors_and_stops_at_limit():
    calls = []
    def opener(request, timeout):
        calls.append(request)
        raise URLError("offline")
    with pytest.raises(RuntimeError, match="after 3 attempts"):
        post_payload("https://collector.example/v1/traces", {}, opener=opener,
                     max_retries=2, sleeper=lambda _: None)
    assert len(calls) == 3


def test_send_directory_posts_both_signals_and_never_reports_secret(tmp_path):
    (tmp_path / "otlp-traces.json").write_text(json.dumps({"resourceSpans": []}), encoding="utf-8")
    (tmp_path / "otlp-metrics.json").write_text(json.dumps({"resourceMetrics": []}), encoding="utf-8")
    urls = []
    def opener(request, timeout):
        urls.append(request.full_url)
        return FakeResponse(202)
    report = send_directory(tmp_path, "https://collector.example:4318/prefix",
                            auth_header="Bearer hidden-secret", opener=opener,
                            sleeper=lambda _: None)
    assert urls == [
        "https://collector.example:4318/prefix/v1/traces",
        "https://collector.example:4318/prefix/v1/metrics",
    ]
    assert report["results"]["traces"]["http_status"] == 202
    assert report["results"]["metrics"]["http_status"] == 202
    assert report["credentials_logged"] is False
    assert "hidden-secret" not in json.dumps(report)


def test_send_directory_rejects_missing_payload(tmp_path):
    (tmp_path / "otlp-traces.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="cannot read OTLP metrics payload"):
        send_directory(tmp_path, "http://localhost:4318", opener=lambda *a, **k: FakeResponse())