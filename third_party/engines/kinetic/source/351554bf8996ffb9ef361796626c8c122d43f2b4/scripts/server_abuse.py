#!/usr/bin/env python3
"""Throws bad input and misbehaving clients at `kinetic serve`.

Every case must end in the expected status (bad input gets a 4xx with a
message, never a crash or a hang) and the server must still answer a real
chat request at the end.

    python scripts/server_abuse.py -- kinetic serve model.gguf -c 512 --port 8091
    python scripts/server_abuse.py --port 8091          # a server already running

Run the server with a small context (-c 512) so the long-prompt case is
quick. --long adds a slow-loris case that waits out the 30 s read timeout.
Standard library only.
"""

import argparse
import concurrent.futures
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

HOST = "127.0.0.1"
PORT = 8091
TIMEOUT = 120
CHAT = "/v1/chat/completions"


def status_of(s):
    head = b""
    while len(head.split(b" ")) < 3:
        chunk = s.recv(64)
        if not chunk:
            break
        head += chunk
    return int(head.split(b" ")[1])


def raw(data, read=True, timeout=TIMEOUT):
    """Sends raw bytes, returns (status, body) of the reply."""
    with socket.create_connection((HOST, PORT), timeout=timeout) as s:
        s.sendall(data)
        if not read:
            return None, b""
        reply = b""
        while True:
            try:
                chunk = s.recv(65536)
            except ConnectionResetError:
                break
            if not chunk:
                break
            reply += chunk
    head, _, body = reply.partition(b"\r\n\r\n")
    try:
        return int(head.split(b" ")[1]), body
    except (IndexError, ValueError):
        return None, reply


def request(method, path, body=None, headers=None, ctype="application/json"):
    if isinstance(body, (dict, list)):
        body = json.dumps(body).encode()
    elif isinstance(body, str):
        body = body.encode()
    head = f"{method} {path} HTTP/1.1\r\nHost: {HOST}\r\n"
    if ctype and body is not None:
        head += f"Content-Type: {ctype}\r\n"
    if body is not None:
        head += f"Content-Length: {len(body)}\r\n"
    for k, v in (headers or {}).items():
        head += f"{k}: {v}\r\n"
    return raw(head.encode() + b"\r\n" + (body or b""))


def chat(**fields):
    body = {"messages": [{"role": "user", "content": "Say hi."}], "max_tokens": 4}
    body.update(fields)
    return request("POST", CHAT, body)


def slow_client():
    body = json.dumps(
        {"messages": [{"role": "user", "content": "Hi"}], "max_tokens": 2}
    ).encode()
    data = (
        f"POST {CHAT} HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    with socket.create_connection((HOST, PORT), timeout=TIMEOUT) as s:
        for i in range(len(data)):
            s.send(data[i : i + 1])
            time.sleep(0.01)
        return status_of(s), b""


def disconnect_mid_stream():
    body = json.dumps(
        {
            "messages": [{"role": "user", "content": "Count to one hundred."}],
            "max_tokens": 200,
            "stream": True,
        }
    ).encode()
    data = (
        f"POST {CHAT} HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    s = socket.create_connection((HOST, PORT), timeout=TIMEOUT)
    s.sendall(data)
    first = s.recv(4096)
    while b" " not in first.lstrip():
        first += s.recv(4096)
    # reset rather than close, the way a killed client looks
    s.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, b"\x01\x00\x00\x00\x00\x00\x00\x00")
    s.close()
    return int(first.split(b" ")[1]), first


def disconnect_before_body():
    head = (
        f"POST {CHAT} HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\n"
        "Content-Length: 1000\r\n\r\n{\"mess"
    ).encode()
    return raw(head, read=False)


def parallel(n, fn):
    with concurrent.futures.ThreadPoolExecutor(n) as pool:
        results = list(pool.map(lambda _: fn(), range(n)))
    return results


def many_connections():
    results = parallel(100, lambda: request("GET", "/health")[0])
    bad = [r for r in results if r not in (200, 503)]
    return (200 if not bad else bad[0]), f"{results.count(200)} ok, {results.count(503)} busy".encode()


def parallel_chats():
    results = parallel(8, lambda: chat(max_tokens=3)[0])
    bad = [r for r in results if r != 200]
    return (200 if not bad else bad[0]), str(results).encode()


def slow_loris():
    with socket.create_connection((HOST, PORT), timeout=60) as s:
        s.sendall(b"POST /v1/chat/completions HTTP/1.1\r\nHost: x\r\n")
        start = time.time()
        reply = s.recv(64)
        return (0 if reply else 200), f"closed after {time.time() - start:.0f} s".encode()


LONG = "word " * 4000
NEST = "[" * 100_000 + "]" * 100_000

CASES = [
    # (name, expected statuses, call)
    ("health", {200}, lambda: request("GET", "/health")),
    ("unknown endpoint", {404}, lambda: request("GET", "/v1/nope")),
    ("unknown ollama endpoint", {404}, lambda: request("POST", "/api/nope", {})),
    ("wrong method", {405}, lambda: request("GET", CHAT)),
    ("malformed json", {400}, lambda: request("POST", CHAT, '{"messages": [')),
    ("empty body", {400}, lambda: request("POST", CHAT, b"")),
    ("no body at all", {400}, lambda: request("POST", CHAT)),
    ("json array body", {400}, lambda: request("POST", CHAT, [1, 2])),
    ("invalid utf-8", {400}, lambda: request("POST", CHAT, b'{"messages": "\xff\xfe"}')),
    ("deep nesting", {400}, lambda: request("POST", CHAT, NEST)),
    ("missing messages", {400}, lambda: request("POST", CHAT, {})),
    ("empty messages", {400}, lambda: chat(messages=[])),
    ("messages is a string", {400}, lambda: chat(messages="hi")),
    ("message without role", {400}, lambda: chat(messages=[{"content": "hi"}])),
    ("content is a number", {400}, lambda: chat(messages=[{"role": "user", "content": 5}])),
    ("unknown role", {200, 400}, lambda: chat(messages=[{"role": "wizard", "content": "hi"}])),
    ("null bytes in content", {200}, lambda: chat(messages=[{"role": "user", "content": "a\u0000b"}])),
    ("max_tokens is a string", {400}, lambda: chat(max_tokens="ten")),
    ("max_tokens negative", {400}, lambda: chat(max_tokens=-1)),
    ("max_tokens zero", {200, 400}, lambda: chat(max_tokens=0)),
    ("max_tokens huge", {200, 400}, lambda: chat(max_tokens=10**12)),
    ("max_tokens beyond u64", {400}, lambda: chat(max_tokens=10**30)),
    ("temperature nan", {400}, lambda: request("POST", CHAT, '{"messages":[{"role":"user","content":"x"}],"temperature":NaN}')),
    ("temperature negative", {200, 400}, lambda: chat(temperature=-5)),
    ("top_p out of range", {200, 400}, lambda: chat(top_p=7)),
    ("n = 2", {400}, lambda: chat(n=2)),
    ("stop is a number", {400}, lambda: chat(stop=5)),
    ("many stop strings", {200, 400}, lambda: chat(stop=["x" * 100] * 1000)),
    ("bad response_format", {400}, lambda: chat(response_format={"type": "xml"})),
    ("bad json schema", {400}, lambda: chat(response_format={"type": "json_schema", "json_schema": {"schema": {"type": "nope"}}})),
    ("schema not an object", {400}, lambda: chat(response_format={"type": "json_schema", "json_schema": 5})),
    ("bad grammar", {400}, lambda: chat(grammar="root ::= (")),
    ("tools not a list", {400}, lambda: chat(tools="f")),
    ("tool without function", {200, 400}, lambda: chat(tools=[{"type": "function"}])),
    ("tool_choice unknown function", {200, 400}, lambda: chat(tools=[{"type": "function", "function": {"name": "f", "parameters": {}}}], tool_choice={"type": "function", "function": {"name": "g"}})),
    ("logprobs", {200, 400}, lambda: chat(logprobs=True, top_logprobs=3)),
    ("top_logprobs huge", {200, 400}, lambda: chat(logprobs=True, top_logprobs=10**6)),
    ("prompt longer than context", {400}, lambda: chat(messages=[{"role": "user", "content": LONG}])),
    ("completion prompt not a string", {400}, lambda: request("POST", "/v1/completions", {"prompt": {"a": 1}})),
    ("completion prompt longer than context", {400}, lambda: request("POST", "/v1/completions", {"prompt": LONG, "max_tokens": 1})),
    ("ollama chat garbage", {400}, lambda: request("POST", "/api/chat", '{"model": 5')),
    ("ollama generate wrong type", {400}, lambda: request("POST", "/api/generate", {"prompt": ["x"]})),
    ("embeddings on a chat model", {400}, lambda: request("POST", "/v1/embeddings", {"input": "x"})),
    ("llama /completion garbage", {400}, lambda: request("POST", "/completion", "{\"prompt\": ")),
    ("llama /completion no prompt", {400}, lambda: request("POST", "/completion", {"n_predict": 4})),
    ("llama /completion prompt object", {400}, lambda: request("POST", "/completion", {"prompt": {"a": 1}})),
    ("llama /completion ids out of range", {200, 400}, lambda: request("POST", "/completion", {"prompt": [4294967295, 2**40], "n_predict": 2})),
    ("llama /completion n_predict string", {200, 400}, lambda: request("POST", "/completion", {"prompt": "x", "n_predict": "4"})),
    ("llama /completion too long, streamed", {200, 400}, lambda: request("POST", "/completion", {"prompt": LONG, "stream": True})),
    ("llama /completion bad grammar", {400}, lambda: request("POST", "/completion", {"prompt": "x", "grammar": "root ::= ["})),
    ("llama /completion bad json_schema", {400}, lambda: request("POST", "/completion", {"prompt": "x", "json_schema": {"type": 5}})),
    ("llama /tokenize content number", {400}, lambda: request("POST", "/tokenize", {"content": 5})),
    ("llama /tokenize broken specials", {200}, lambda: request("POST", "/tokenize", {"content": "<|im_start|><|im_e \u0000 🦀", "with_pieces": True})),
    ("llama /detokenize negative ids", {400}, lambda: request("POST", "/detokenize", {"tokens": [-1]})),
    ("llama /detokenize unknown ids", {200}, lambda: request("POST", "/detokenize", {"tokens": [4294967295, 0, 99999999]})),
    ("llama /tokenize from a web page", {403}, lambda: request("POST", "/tokenize", {"content": "x"}, headers={"Origin": "https://evil.example"})),
    ("llama /props", {200}, lambda: request("GET", "/props")),
    ("llama /slots", {200}, lambda: request("GET", "/slots")),
    ("llama /props wrong method", {405}, lambda: request("POST", "/props", {})),
    ("llama /embedding on a chat model", {400, 501}, lambda: request("POST", "/embedding", {"content": "x"})),
    ("ollama /api/show garbage", {400}, lambda: request("POST", "/api/show", "[")),
    ("ollama /api/ps", {200}, lambda: request("GET", "/api/ps")),
    ("ollama /api/chat options junk", {200, 400}, lambda: request("POST", "/api/chat", {"messages": [{"role": "user", "content": "hi"}], "stream": False, "options": {"num_predict": "x", "num_ctx": -5, "temperature": None}})),
    ("ollama /api/chat images junk", {400}, lambda: request("POST", "/api/chat", {"messages": [{"role": "user", "content": "hi", "images": ["%%%"]}], "stream": False})),
    ("ollama /api/generate too long", {400}, lambda: request("POST", "/api/generate", {"prompt": LONG, "stream": False})),
    ("ollama /api/generate format schema bad", {400}, lambda: request("POST", "/api/generate", {"prompt": "x", "format": {"type": "nope"}, "stream": False})),
    ("text/plain body", {415}, lambda: request("POST", CHAT, "{}", ctype="text/plain")),
    ("content-length not a number", {400}, lambda: raw(b"POST /v1/chat/completions HTTP/1.1\r\nContent-Length: abc\r\n\r\n")),
    ("content-length negative", {400}, lambda: raw(b"POST /v1/chat/completions HTTP/1.1\r\nContent-Length: -5\r\n\r\n")),
    ("body over the limit", {413}, lambda: raw(b"POST /v1/chat/completions HTTP/1.1\r\nContent-Length: 999999999999\r\n\r\n")),
    ("chunked body", {411}, lambda: raw(b"POST /v1/chat/completions HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n0\r\n\r\n")),
    ("garbage request line", {400}, lambda: raw(b"\x00\x01\x02 hello\r\n\r\n")),
    ("http/2 preface", {400, 505}, lambda: raw(b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n")),
    ("huge header", {431}, lambda: raw(b"GET /health HTTP/1.1\r\nX: " + b"a" * 40000 + b"\r\n\r\n")),
    ("many headers", {431}, lambda: raw(b"GET /health HTTP/1.1\r\n" + b"X: y\r\n" * 500 + b"\r\n")),
    ("15 MB of junk json", {400}, lambda: request("POST", CHAT, b"{" * (15 * 1024 * 1024))),
    ("client sends a byte at a time", {200}, slow_client),
    ("disconnect before the body", {None}, disconnect_before_body),
    ("disconnect mid-stream", {200}, disconnect_mid_stream),
    ("100 parallel connections", {200}, many_connections),
    ("8 parallel chats", {200}, parallel_chats),
    ("health after the abuse", {200}, lambda: request("GET", "/health")),
    ("real chat after the abuse", {200}, lambda: chat(max_tokens=8)),
]


def main():
    global PORT
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--port", type=int, default=PORT)
    p.add_argument("--long", action="store_true", help="add the 30 s slow-loris case")
    p.add_argument("server", nargs=argparse.REMAINDER, help="-- command that starts the server")
    args = p.parse_args()
    PORT = args.port
    cases = list(CASES)
    if args.long:
        cases.insert(-2, ("slow loris is cut off", {200}, slow_loris))

    proc = None
    if args.server:
        cmd = args.server[1:] if args.server[0] == "--" else args.server
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        deadline = time.time() + 300
        while True:
            try:
                urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=2)
                break
            except (urllib.error.URLError, ConnectionError, OSError):
                if proc.poll() is not None or time.time() > deadline:
                    sys.exit(f"server did not start:\n{proc.stderr.read().decode(errors='replace')}")
                time.sleep(0.5)

    failures = 0
    try:
        for name, expected, call in cases:
            start = time.time()
            try:
                status, body = call()
            except Exception as e:  # a reset or a timeout is a failure too
                status, body = repr(e), b""
            took = time.time() - start
            ok = status in expected
            if proc is not None and proc.poll() is not None:
                ok, body = False, b"server exited: " + proc.stderr.read()
            failures += not ok
            detail = body[:160].decode(errors="replace").replace("\n", " ")
            print(f"{'ok  ' if ok else 'FAIL'} {status!s:>4} {took:5.1f}s  {name}  {detail}")
            if proc is not None and proc.poll() is not None:
                break
    finally:
        if proc is not None:
            proc.kill()
            proc.wait()
    print(f"{len(cases) - failures} of {len(cases)} passed")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
