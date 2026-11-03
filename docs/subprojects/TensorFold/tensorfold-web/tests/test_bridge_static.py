#!/usr/bin/env python3
"""Standard-library smoke tests for TensorFold Web's static file handler."""
import importlib.util
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SOURCE = Path(__file__).resolve().parents[1] / "tensorfold-web-bridge.py"
SPEC = importlib.util.spec_from_file_location("tensorfold_web_bridge", SOURCE)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

class BridgeStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        (cls.root / "index.html").write_text("<h1>TensorFold Web test</h1>")
        (cls.root / "tensorfold-logo.png").write_bytes(b"\x89PNG\r\n\x1a\nfake-test-image")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), MODULE.Handler)
        cls.server.web_root = cls.root
        cls.server.engine = urlparse("http://127.0.0.1:1")
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=2)
        cls.temp.cleanup()

    def test_root_serves_index(self):
        with urlopen(self.base + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"TensorFold Web test", response.read())

    def test_root_query_string_still_serves_index(self):
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

    def test_engine_unavailable_returns_502(self):
        with self.assertRaises(HTTPError) as caught:
            urlopen(self.base + "/api/health")
        self.assertEqual(caught.exception.code, 502)

if __name__ == "__main__":
    unittest.main(verbosity=2)
