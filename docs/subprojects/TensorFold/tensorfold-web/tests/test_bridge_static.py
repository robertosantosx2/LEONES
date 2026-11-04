#!/usr/bin/env python3
"""Standard-library integration tests for TensorFold Web's bridge."""
import importlib.util
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SOURCE = Path(__file__).resolve().parents[1] / "tensorfold-web-bridge.py"
SPEC = importlib.util.spec_from_file_location("tensorfold_web_bridge", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class FakeEngineHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.server.last_path = self.path
        payload = ('<!doctype html><script>const STATS_URL = location.pathname.replace(/\\/(dashboard)?\\/?$/, "") + "/stats?poll=1";</script>'
                   if self.path == "/dashboard" else
                   json.dumps({"status": "ok", "model": "test-model"})
                   if self.path == "/health" else
                   json.dumps({"data": [{"id": "test-model"}]})
                   if self.path == "/v1/models" else
                   json.dumps({"tokens_per_second": 12.5})
                   if self.path in ("/stats", "/stats?poll=1") else None)
        if payload is None:
            self.send_error(404)
            return
        body = payload.encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        self.server.last_request = request
        body = (b'data: {"choices":[{"delta":{"content":"hello"}}]}\n\n'
                b'data: [DONE]\n\n')
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

class BridgeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "index.html").write_text("<h1>TensorFold Web test</h1>")
        (cls.root / "tensorfold-logo.png").write_bytes(bytes.fromhex("89504e470d0a1a0a") + b"fake-test-image")
        (cls.root / "manifest.webmanifest").write_text(json.dumps({"name": "TensorFold Web"}))
        (cls.root / "service-worker.js").write_text('if (url.pathname.startsWith("/api/")) return;')
        (cls.root / "tensorfold-web-icon.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>')

        cls.engine = ThreadingHTTPServer(("127.0.0.1", 0), FakeEngineHandler)
        cls.engine.last_request = None
        cls.engine_thread = threading.Thread(target=cls.engine.serve_forever, daemon=True)
        cls.engine_thread.start()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MODULE.Handler)
        cls.server.web_root = cls.root
        cls.server.engine_process = None
        cls.server.engine_lock = threading.Lock()
        cls.server.engine_log_path = str(cls.root / "engine.log")
        cls.server.engine = urlparse("http://127.0.0.1:" + str(cls.engine.server_port))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.engine.shutdown()
        cls.engine.server_close()
        cls.engine_thread.join(timeout=2)
        cls.temp.cleanup()

    def test_engine_status_and_log_routes(self):
        with urlopen(self.base + "/api/engine/status") as response:
            status = json.load(response)
        self.assertFalse(status["running"])
        with urlopen(self.base + "/api/engine/log") as response:
            self.assertEqual(json.load(response)["log"], "")

    def test_engine_manager_ui_is_present(self):
        index = SOURCE.with_name("index.html").read_text(encoding="utf-8")
        for element in ("engineBinary", "engineModel", "inspectEngine", "startEngine", "stopEngine"):
            self.assertIn('id="' + element + '"', index)

    def test_engine_control_routes_are_present(self):
        bridge = SOURCE.read_text(encoding="utf-8")
        for route in ("/api/engine/inspect", "/api/engine/start", "/api/engine/stop", "/api/engine/status"):
            self.assertIn(route, bridge)

    def test_workspace_navigation_views_are_present(self):
        index = SOURCE.with_name("index.html").read_text(encoding="utf-8")
        for view in ("chat", "models", "dashboard", "bots", "history", "projects", "server", "api", "settings"):
            self.assertIn('data-view="' + view + '"', index)
            self.assertIn('id="view-' + view + '"', index)

    def test_pwa_manifest_is_served_as_json(self):
        with urlopen(self.base + "/manifest.webmanifest") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["name"], "TensorFold Web")

    def test_service_worker_is_served_and_bypasses_api(self):
        with urlopen(self.base + "/service-worker.js") as response:
            body = response.read().decode()
            self.assertIn('url.pathname.startsWith("/api/")', body)

    def test_pwa_icon_is_served_as_svg(self):
        with urlopen(self.base + "/tensorfold-web-icon.svg") as response:
            self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
            self.assertIn(b"<svg", response.read())

    def test_pwa_registration_is_present_in_frontend(self):
        index = SOURCE.with_name("index.html").read_text(encoding="utf-8")
        self.assertIn('rel="manifest"', index)
        self.assertIn("navigator.serviceWorker.register('/service-worker.js')", index)

    def test_pake_config_targets_local_bridge(self):
        config = json.loads(SOURCE.with_name("pake.config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["url"], "http://127.0.0.1:8787/")
        self.assertEqual(config["targets"], "deb,appimage")
        self.assertTrue(config["keepBinary"])

    def test_root_serves_index(self):
        with urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"TensorFold Web test", response.read())

    def test_root_query_string_serves_index(self):
        with urlopen(self.base + "/?source=test") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"TensorFold Web test", response.read())

    def test_png_get_has_image_mime_type(self):
        with urlopen(self.base + "/tensorfold-logo.png") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(response.read().startswith(b"\x89PNG"))

    def test_png_head_returns_headers_without_body(self):
        request = Request(self.base + "/tensorfold-logo.png", method="HEAD")
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertGreater(int(response.headers["Content-Length"]), 0)
            self.assertEqual(response.read(), b"")

    def test_missing_file_returns_404(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/missing.png")
        self.assertEqual(caught.exception.code, 404)

    def test_encoded_parent_path_is_rejected(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/%2e%2e/secret.txt")
        self.assertEqual(caught.exception.code, 403)

    def test_health_route_proxies_engine(self):
        with urlopen(self.base + "/api/health") as response:
            self.assertEqual(json.load(response)["status"], "ok")

    def test_stats_route_proxies_engine(self):
        with urlopen(self.base + "/api/stats") as response:
            self.assertEqual(json.load(response)["tokens_per_second"], 12.5)

    def test_native_dashboard_route_proxies_engine_page(self):
        with urlopen(self.base + "/api/dashboard") as response:
            body = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn("STATS_URL", body)
            self.assertEqual(self.engine.last_path, "/dashboard")

    def test_native_dashboard_poll_query_reaches_stats(self):
        with urlopen(self.base + "/api/stats?poll=1") as response:
            self.assertEqual(json.load(response)["tokens_per_second"], 12.5)
            self.assertEqual(self.engine.last_path, "/stats?poll=1")

    def test_models_route_proxies_engine(self):
        with urlopen(self.base + "/api/v1/models") as response:
            self.assertEqual(json.load(response)["data"][0]["id"], "test-model")

    def test_chat_post_forwards_json_and_sse(self):
        payload = json.dumps({"model": "test-model", "messages": [{"role": "user", "content": "hi"}],
                              "stream": True}).encode()
        request = Request(self.base + "/api/v1/chat/completions", data=payload,
                          headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            body = response.read()
            self.assertEqual(response.headers.get_content_type(), "text/event-stream")
            self.assertIn(b'"content":"hello"', body)
            self.assertIn(b"data: [DONE]", body)
        self.assertEqual(self.engine.last_request["model"], "test-model")

    def test_unknown_api_post_is_404(self):
        request = Request(self.base + "/api/unknown", data=b"{}", method="POST")
        with self.assertRaises(HTTPError) as caught:
            urlopen(request)
        self.assertEqual(caught.exception.code, 404)

if __name__ == "__main__":
    unittest.main(verbosity=2)
