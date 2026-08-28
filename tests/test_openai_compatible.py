import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from scripts.openai_compatible import OpenAICompatibleEndpoint, chat, health, list_models


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload, status=200):
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        if self.path == "/v1/models":
            self._send({"object": "list", "data": [{"id": "test-model"}]})
            return
        self._send({"error": "not found"}, 404)

    def do_POST(self):
        assert self.path == "/v1/chat/completions"
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert body["model"] == "test-model"
        assert body["stream"] is False
        self._send(
            {
                "id": "req-test-1",
                "choices": [{"message": {"role": "assistant", "content": "ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            }
        )

    def log_message(self, *_args):
        pass


@pytest.fixture
def endpoint():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield OpenAICompatibleEndpoint(
            f"http://127.0.0.1:{server.server_port}/v1",
            "test-model",
            api_key="local-test-key",
        )
    finally:
        server.shutdown()
        thread.join()


def test_endpoint_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        OpenAICompatibleEndpoint("", "model")
    with pytest.raises(ValueError):
        OpenAICompatibleEndpoint("http://localhost", "")
    with pytest.raises(ValueError):
        OpenAICompatibleEndpoint("http://localhost", "model", timeout_seconds=0)


def test_endpoint_accepts_root_or_v1_url():
    root = OpenAICompatibleEndpoint("http://localhost:8080", "model")
    versioned = OpenAICompatibleEndpoint("http://localhost:8080/v1/", "model")
    assert root.normalized_base_url == "http://localhost:8080"
    assert versioned.normalized_base_url == "http://localhost:8080"


def test_health_uses_models_endpoint(endpoint):
    result = health(endpoint)
    assert result["http_status"] == 200
    assert result["base_url"].endswith("/v1")
    assert result["models"][0]["id"] == "test-model"


def test_list_models_returns_advertised_models(endpoint):
    assert list_models(endpoint) == [{"id": "test-model"}]


def test_chat_is_non_streaming_and_preserves_observed_metadata(endpoint):
    result = chat(endpoint, [{"role": "user", "content": "hello"}], max_tokens=8)
    assert result["provider_id"] == "openai-compatible"
    assert result["request_id"] == "req-test-1"
    assert result["response_status"] == 200
    assert result["usage"]["total_tokens"] == 4
    assert result["latency_seconds"] >= 0


def test_chat_rejects_invalid_requests(endpoint):
    with pytest.raises(ValueError):
        chat(endpoint, [])
    with pytest.raises(ValueError):
        chat(endpoint, [{"role": "user", "content": "hello"}], max_tokens=0)
