#!/usr/bin/env python3
"""Dependency-free TensorFold Native smoke test for the Atomic Chat integration spike.

Usage:
  python3 poc.py /path/to/model-directory

Environment:
  TENSORFOLD_BIN       Native executable (default: TensorFold 1.2.3 user install)
  TENSORFOLD_CONTEXT   Context length (default: 2048)
  TENSORFOLD_TIMEOUT   Startup timeout in seconds (default: 300)
"""
from __future__ import annotations

import collections
import json
import math
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_BIN = Path.home() / ".local/opt/tensorfold-1.2.3-linux-x86_64/bin/tensorfold-native"
BIN = Path(os.environ.get("TENSORFOLD_BIN", str(DEFAULT_BIN))).expanduser()
CONTEXT = int(os.environ.get("TENSORFOLD_CONTEXT", "2048"))
TIMEOUT = int(os.environ.get("TENSORFOLD_TIMEOUT", "300"))
MIN_FREE_MIB = int(os.environ.get("TENSORFOLD_MIN_FREE_MIB", "3072"))
MODEL = sys.argv[1] if len(sys.argv) > 1 else ""


def fail(message: str) -> None:
    raise RuntimeError(message)


def request(url: str, payload: dict | None = None, timeout: float = 10):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.status, response.read()


def gpu_free_memory_mib() -> int:
    """Read GPU 0 free VRAM without changing any running process."""
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        check=True, text=True, capture_output=True, timeout=10,
    )
    first = result.stdout.strip().splitlines()[0]
    return int(first.strip())


def checkpoint_memory_floor_mib(info_output: str) -> int:
    """Parse TensorFold info's documented weights-plus-runtime memory floor."""
    match = re.search(r"^memory floor:\\s*([0-9]+(?:\\.[0-9]+)?)\\s+GiB\\b", info_output, re.MULTILINE)
    if match is None:
        fail("tensorfold info did not report a native checkpoint memory floor")
    return math.ceil(float(match.group(1)) * 1024)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def build_command(model: str, port: int, name: str = "atomic-tensorfold-poc") -> list[str]:
    """Build a loopback-only, single-slot CUDA server command without shell parsing."""
    return [
        str(BIN), "serve", model,
        "--name", name,
        "--host", "127.0.0.1",
        "--port", str(port),
        "--parallel", "1",
        "--context", str(CONTEXT),
        "--backend", "cuda",
        "--no-update-check",
    ]


def main() -> int:
    if not MODEL:
        fail("Pass an already-downloaded local TensorFold checkpoint directory or cached repository ID.")
    if not BIN.is_file() or not os.access(BIN, os.X_OK):
        fail(f"TensorFold executable is missing or not executable: {BIN}")

    print(f"[1/6] Binary: {BIN}")
    version = subprocess.run([str(BIN), "--version"], check=True, text=True, capture_output=True)
    print(version.stdout.strip() or version.stderr.strip())

    print("[2/6] Reading native capabilities")
    caps = subprocess.run([str(BIN), "capabilities", "--json"], check=True, text=True, capture_output=True)
    try:
        capabilities = json.loads(caps.stdout)
    except json.JSONDecodeError:
        fail("capabilities --json did not return valid JSON")
    print(json.dumps(capabilities, indent=2)[:6000])
    if "cuda" not in capabilities.get("backends", []):
        fail("This TensorFold binary does not declare the CUDA backend")

    print("[Checkpoint preflight] inspecting this exact checkpoint without loading it")
    info = subprocess.run([str(BIN), "info", MODEL], text=True, capture_output=True)
    info_output = info.stdout + info.stderr
    print(info_output.strip()[:3000])
    if info.returncode != 0:
        fail("TensorFold info rejected this checkpoint; it is not eligible for the native engine")
    checkpoint_floor_mib = checkpoint_memory_floor_mib(info_output)
    print(f"[Checkpoint preflight] documented memory floor: {checkpoint_floor_mib} MiB")

    free_mib = gpu_free_memory_mib()
    print(f"[GPU preflight] free VRAM: {free_mib} MiB; required safety floor: {MIN_FREE_MIB} MiB")
    if checkpoint_floor_mib > free_mib:
        fail(f"Checkpoint memory floor {checkpoint_floor_mib} MiB exceeds currently free VRAM {free_mib} MiB")
    if free_mib < MIN_FREE_MIB:
        fail(
            f"Only {free_mib} MiB VRAM is free; refusing to start a model load "
            f"below the {MIN_FREE_MIB} MiB safety floor. Close/release GPU workloads "
            "yourself, or set TENSORFOLD_MIN_FREE_MIB deliberately if you accept the risk."
        )

    port = free_port()
    command = build_command(MODEL, port)
    print(f"[3/6] Starting child process on 127.0.0.1:{port}")
    print("argv:", json.dumps(command))
    child = subprocess.Popen(
        command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    logs = collections.deque(maxlen=160)

    def drain():
        assert child.stdout is not None
        for line in child.stdout:
            logs.append(line.rstrip())

    reader = threading.Thread(target=drain, daemon=True)
    reader.start()
    base = f"http://127.0.0.1:{port}"

    try:
        deadline = time.monotonic() + TIMEOUT
        ready = False
        while time.monotonic() < deadline:
            if child.poll() is not None:
                fail(f"TensorFold exited during startup (code {child.returncode})")
            try:
                status, body = request(base + "/health", timeout=2)
                if 200 <= status < 300:
                    ready = True
                    print("[4/6] /health:", body.decode(errors="replace")[:1000])
                    break
            except (OSError, urllib.error.URLError, TimeoutError):
                time.sleep(0.5)
        if not ready:
            fail(f"TensorFold did not become ready within {TIMEOUT}s")

        status, raw_models = request(base + "/v1/models")
        models = json.loads(raw_models)
        entries = models.get("data", [])
        if not entries or not isinstance(entries[0].get("id"), str):
            fail(f"/v1/models returned no usable model ID: {models}")
        model_id = entries[0]["id"]
        print("[5/6] /v1/models:", json.dumps(models)[:2000])

        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with exactly: ATOMIC_TENSORFOLD_OK"}],
            "max_tokens": 64,
            "temperature": 0,
        }
        status, raw = request(base + "/v1/chat/completions", payload, timeout=120)
        answer = json.loads(raw)
        text = answer.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not isinstance(text, str) or not text.strip():
            fail(f"Non-streaming chat returned no text: {answer}")
        print("non-stream response:", text[:1000])

        stream_payload = dict(payload, stream=True)
        req = urllib.request.Request(
            base + "/v1/chat/completions",
            data=json.dumps(stream_payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as response:
            stream_body = response.read().decode(errors="replace")
        if "data: [DONE]" not in stream_body:
            fail("Streaming response did not contain the OpenAI-compatible data: [DONE] terminator")
        print("[6/6] Streaming: PASS (SSE data: [DONE] received)")
        print("RESULT: PASS — health, model discovery, chat and streaming")
        return 0
    finally:
        if child.poll() is None:
            child.send_signal(signal.SIGTERM)
            try:
                child.wait(timeout=10)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5)
        reader.join(timeout=1)
        print("\n--- TensorFold process log (tail) ---")
        for line in logs:
            print(line)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"RESULT: FAIL — {exc}", file=sys.stderr)
        raise SystemExit(1)
