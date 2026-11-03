#!/usr/bin/env python3
"""Dependency-free TensorFold Web static server and Engine API bridge."""
from __future__ import annotations
import argparse, http.client, json, mimetypes, os, sys, subprocess, threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, urlsplit

VERSION = "0.2.0"

class Handler(BaseHTTPRequestHandler):
    server_version = "TensorFoldWeb/0.2"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def error(self, status, message):
        body = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def proxy(self, path, method="GET", body=None):
        engine = self.server.engine
        try:
            conn_type = http.client.HTTPSConnection if engine.scheme == "https" else http.client.HTTPConnection
            default_port = 443 if engine.scheme == "https" else 80
            conn = conn_type(engine.hostname, engine.port or default_port,
                              timeout=300 if method == "POST" else 15)
            headers = {}
            if self.headers.get("Content-Type"):
                headers["Content-Type"] = self.headers["Content-Type"]
            if body is not None:
                headers["Content-Length"] = str(len(body))
            conn.request(method, path, body=body, headers=headers)
            response = conn.getresponse()
            self.send_response(response.status, response.reason)
            for key, value in response.getheaders():
                if key.lower() not in {"connection", "transfer-encoding", "content-length",
                    "keep-alive", "proxy-authenticate", "proxy-authorization", "te",
                    "trailers", "upgrade", "server", "date"}:
                    self.send_header(key, value)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            if method != "HEAD":
                while True:
                    chunk = response.read1(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            conn.close()
        except (OSError, http.client.HTTPException) as exc:
            self.error(502, "TensorFold Engine unavailable: " + str(exc))

    def static(self, head=False):
        raw = unquote(urlsplit(self.path).path)
        rel = "index.html" if raw in ("", "/") else raw.lstrip("/")
        target = (self.server.web_root / rel).resolve()
        try:
            target.relative_to(self.server.web_root)
        except ValueError:
            self.error(403, "Forbidden path")
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self.error(404, "Not found")
            return
        try:
            size = target.stat().st_size
            kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            if kind.startswith("text/") or kind in ("application/javascript", "application/json"):
                kind += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(size))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            if not head:
                with target.open("rb") as stream:
                    while True:
                        chunk = stream.read(65536)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
        except OSError as exc:
            self.error(500, "Static file error: " + str(exc))

    def json_response(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 1 or length > 1024 * 1024:
                raise ValueError("Request body must be between 1 byte and 1 MiB")
            return json.loads(self.rfile.read(length))
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid JSON request: " + str(exc))

    def do_GET(self):
        if urlsplit(self.path).path == "/api/engine/log":
            try:
                with open(self.server.engine_log_path, "r", encoding="utf-8", errors="replace") as stream:
                    content = stream.read()[-24000:]
            except OSError:
                content = ""
            self.json_response(200, {"log": content})
            return
        if urlsplit(self.path).path == "/api/engine/status":
            proc = self.server.engine_process
            running = proc is not None and proc.poll() is None
            self.json_response(200, {"managed": proc is not None, "running": running,
                "pid": proc.pid if running else None,
                "returncode": proc.poll() if proc is not None and not running else None,
                "log": self.server.engine_log_path})
            return
        routes = {"/api/health": "/health", "/api/stats": "/stats",
                  "/api/dashboard": "/dashboard", "/api/v1/models": "/v1/models"}
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in routes:
            target = routes[path] + (("?" + parsed.query) if parsed.query else "")
            self.proxy(target)
        else:
            self.static()

    def do_HEAD(self):
        routes = {"/api/health": "/health", "/api/stats": "/stats",
                  "/api/dashboard": "/dashboard", "/api/v1/models": "/v1/models"}
        parsed = urlsplit(self.path)
        path = parsed.path
        if path in routes:
            target = routes[path] + (("?" + parsed.query) if parsed.query else "")
            self.proxy(target, "HEAD")
        else:
            self.static(head=True)

    def do_POST(self):
        path = urlsplit(self.path).path
        if path in ("/api/engine/inspect", "/api/engine/start", "/api/engine/stop"):
            if self.client_address[0] not in ("127.0.0.1", "::1"):
                self.error(403, "Engine process control is restricted to localhost")
                return
            try:
                data = self.read_json() if path != "/api/engine/stop" else {}
                if path == "/api/engine/inspect":
                    binary = Path(str(data.get("binary", "")).strip()).expanduser().resolve()
                    if not binary.is_file() or not os.access(binary, os.X_OK):
                        self.error(400, "Executable not found or not executable")
                        return
                    caps = subprocess.run([str(binary), "capabilities", "--json"],
                        capture_output=True, text=True, timeout=15)
                    help_result = subprocess.run([str(binary), "serve", "--help"],
                        capture_output=True, text=True, timeout=15)
                    self.json_response(200, {"capabilities": caps.stdout,
                        "capabilities_error": caps.stderr if caps.returncode else "",
                        "help": (help_result.stdout + help_result.stderr).strip(),
                        "help_returncode": help_result.returncode,
                        "binary": str(binary)})
                    return
                with self.server.engine_lock:
                    proc = self.server.engine_process
                    if path == "/api/engine/stop":
                        if proc is None or proc.poll() is not None:
                            self.json_response(200, {"running": False, "message": "No managed engine process"})
                            return
                        proc.terminate()
                        try:
                            proc.wait(timeout=12)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                            proc.wait(timeout=5)
                        self.server.engine_process = None
                        self.json_response(200, {"running": False, "message": "Managed engine stopped"})
                        return
                    if proc is not None and proc.poll() is None:
                        self.error(409, "A TensorFold process is already managed by this Web UI")
                        return
                    binary = Path(str(data.get("binary", "")).strip()).expanduser().resolve()
                    model = str(data.get("model", "")).strip()
                    args = data.get("args", [])
                    if not binary.is_file() or not os.access(binary, os.X_OK):
                        self.error(400, "Executable not found or not executable")
                        return
                    if not model or len(model) > 2048 or "\x00" in model:
                        self.error(400, "A valid model path or repository ID is required")
                        return
                    if not isinstance(args, list) or len(args) > 160 or any(
                        not isinstance(arg, str) or "\x00" in arg or len(arg) > 4096 for arg in args):
                        self.error(400, "Invalid argument list")
                        return
                    command = [str(binary), "serve", model] + args
                    log_path = self.server.engine_log_path
                    log_stream = open(log_path, "a", encoding="utf-8")
                    try:
                        proc = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                            stdout=log_stream, stderr=subprocess.STDOUT,
                            start_new_session=True, close_fds=True)
                    finally:
                        log_stream.close()
                    self.server.engine_process = proc
                    self.json_response(202, {"running": True, "pid": proc.pid,
                        "command": command, "log": log_path,
                        "message": "TensorFold launch requested; waiting for health check"})
                    return
            except subprocess.TimeoutExpired:
                self.error(504, "TensorFold CLI inspection timed out")
            except (OSError, ValueError, TypeError) as exc:
                self.error(400, str(exc))
            return
        if path != "/api/v1/chat/completions":
            self.error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.error(400, "Invalid Content-Length")
            return
        if length < 1 or length > 8 * 1024 * 1024:
            self.error(413, "Request body must be between 1 byte and 8 MiB")
            return
        self.proxy("/v1/chat/completions", "POST", self.rfile.read(length))

def main():
    parser = argparse.ArgumentParser(description="TensorFold Web local interface")
    parser.add_argument("--web-root", default=str(Path(__file__).resolve().parent))
    parser.add_argument("--engine-url", default=os.environ.get("TENSORFOLD_ENGINE_URL", "http://127.0.0.1:8080"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    engine = urlparse(args.engine_url)
    if engine.scheme not in ("http", "https") or not engine.hostname:
        parser.error("--engine-url must be an http(s) URL")
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    root = Path(args.web_root).expanduser().resolve()
    if not root.is_dir():
        parser.error("web root does not exist: " + str(root))
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.daemon_threads = True
    server.web_root, server.engine = root, engine
    server.engine_process = None
    server.engine_lock = threading.Lock()
    server.engine_log_path = str(Path.home() / ".local" / "state" / "tensorfold-web" / "engine.log")
    Path(server.engine_log_path).parent.mkdir(parents=True, exist_ok=True)
    print("TensorFold Web " + VERSION)
    print("Web:    http://" + args.host + ":" + str(args.port) + "/")
    print("Engine: " + args.engine_url)
    print("Files:  " + str(root))
    if args.host not in ("127.0.0.1", "::1", "localhost"):
        print("WARNING: non-loopback bind; add authentication and TLS before network exposure.", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping TensorFold Web.")
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
