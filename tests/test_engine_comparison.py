from __future__ import annotations
import http.server
import pathlib
import sys
import tempfile
import threading
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import engine_comparison as ec


class EngineComparisonTests(unittest.TestCase):
    def test_directory_artifact_hash_is_stable_and_content_sensitive(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            (root / "config.json").write_text("{}")
            (root / "weights.bin").write_bytes(b"weights-a")
            first, count = ec.artifact_sha256(root)
            second, count2 = ec.artifact_sha256(root)
            self.assertEqual(first, second)
            self.assertEqual(count, 2)
            self.assertEqual(count2, 2)
            (root / "weights.bin").write_bytes(b"weights-b")
            changed, count3 = ec.artifact_sha256(root)
            self.assertNotEqual(first, changed)
            self.assertEqual(count3, 2)

    def test_file_artifact_hash_and_empty_directory(self):
        with tempfile.TemporaryDirectory() as td:
            root = pathlib.Path(td)
            file_path = root / "model.gguf"
            file_path.write_bytes(b"model")
            self.assertEqual(ec.artifact_sha256(file_path), (ec.sha256(file_path), 1))
            empty = root / "empty"
            empty.mkdir()
            digest, count = ec.artifact_sha256(empty)
            self.assertEqual(count, 0)
            self.assertTrue(digest)

    def test_render_and_memory_delta(self):
        fields = {"ctx": 512, "port": 1234}
        self.assertEqual(ec.render(["--ctx", "{ctx}", "--port", "{port}"], fields),
                         ["--ctx", "512", "--port", "1234"])
        self.assertEqual(ec.mib_delta({"MemAvailable:": 2 * 1048576},
                                      {"MemAvailable:": 1 * 1048576},
                                      "MemAvailable:"), 1.0)

    def test_gpu_telemetry_parser(self):
        snapshot = {"nvidia_smi": {"stdout": "NVIDIA GeForce RTX 3050 Laptop GPU, 4096, 512, 7, 44, 20.0, 580.178.04"}}
        values = ec.gpu_values(snapshot)
        self.assertEqual(values["name"], "NVIDIA GeForce RTX 3050 Laptop GPU")
        self.assertEqual(values["memory_total_mib"], 4096)
        self.assertEqual(values["memory_used_mib"], 512)
        self.assertEqual(values["util_pct"], 7)

    def test_streaming_metrics_from_openai_sse(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                events = [
                    'data: {"choices":[{"delta":{"content":"Hola"}}]}\n\n',
                    'data: {"choices":[{"delta":{"content":"."}}]}\n\n',
                    'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":2}}\n\n',
                    "data: [DONE]\n\n",
                ]
                for event in events:
                    self.wfile.write(event.encode())
                    self.wfile.flush()
            def log_message(self, *_args):
                pass

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = ec.stream_request(
                f"http://127.0.0.1:{server.server_port}", "/v1/chat/completions", None,
                [{"role": "user", "content": "saluda"}],
                {"temperature": 0, "top_p": 1, "seed": 42, "max_tokens": 8}, 5,
            )
            self.assertEqual(result["text"], "Hola.")
            self.assertEqual(result["prompt_tokens"], 12)
            self.assertEqual(result["completion_tokens"], 2)
            self.assertIsNotNone(result["ttft_s"])
            self.assertIsNotNone(result["prefill_tokens_per_s"])
            self.assertEqual(result["stream_fragments"], 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
