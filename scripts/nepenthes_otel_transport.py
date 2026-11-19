#!/usr/bin/env python3
"""Send prepared OTLP/JSON payloads to an OTLP/HTTP collector.

Remote endpoints must use HTTPS. Credentials are read only from an environment
variable and are never included in logs or the transport report.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


RETRYABLE_STATUS = {429, 500, 502, 503, 504}
LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}


def validate_endpoint(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OTLP endpoint must be an absolute http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OTLP endpoint must not embed credentials, query parameters or fragments")
    if parsed.scheme == "http" and parsed.hostname not in LOOPBACK_HOSTS:
        raise ValueError("remote OTLP endpoints must use HTTPS")
    return value.rstrip("/")


def post_payload(url: str, payload: dict[str, Any], *, auth_header: str | None = None,
                 timeout_seconds: float = 10.0, max_retries: int = 3,
                 backoff_seconds: float = 0.5,
                 opener: Callable[..., Any] = urlopen,
                 sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    if timeout_seconds <= 0 or max_retries < 0 or backoff_seconds < 0:
        raise ValueError("invalid timeout/retry configuration")
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode("utf-8")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if auth_header:
        headers["Authorization"] = auth_header
    attempts = 0
    while True:
        attempts += 1
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with opener(request, timeout=timeout_seconds) as response:
                status = getattr(response, "status", None)
                if status is None:
                    status = response.getcode()
                if status not in {200, 202}:
                    raise RuntimeError(f"OTLP collector returned HTTP {status}")
                return {"status": "success", "http_status": status, "attempts": attempts}
        except HTTPError as exc:
            if exc.code not in RETRYABLE_STATUS or attempts > max_retries:
                raise RuntimeError(f"OTLP collector rejected payload with HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            if attempts > max_retries:
                raise RuntimeError(f"OTLP collector transport failed after {attempts} attempts: {type(exc).__name__}") from exc
        if attempts <= max_retries:
            sleeper(backoff_seconds * (2 ** (attempts - 1)))


def send_directory(input_dir: Path, endpoint: str, *, auth_header: str | None = None,
                   timeout_seconds: float = 10.0, max_retries: int = 3,
                   backoff_seconds: float = 0.5, opener: Callable[..., Any] = urlopen,
                   sleeper: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    base = validate_endpoint(endpoint)
    results = {}
    for signal, filename in (("traces", "otlp-traces.json"), ("metrics", "otlp-metrics.json")):
        path = input_dir / filename
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"cannot read OTLP {signal} payload {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"OTLP {signal} payload must be a JSON object")
        results[signal] = post_payload(
            f"{base}/v1/{signal}", payload, auth_header=auth_header,
            timeout_seconds=timeout_seconds, max_retries=max_retries,
            backoff_seconds=backoff_seconds, opener=opener, sleeper=sleeper,
        )
    parsed = urlsplit(base)
    safe_origin = f"{parsed.scheme}://{parsed.netloc}"
    return {"schema_version": "1.0", "endpoint_origin": safe_origin,
            "results": results, "credentials_logged": False}


def positive_float(value: str) -> float:
    number = float(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--endpoint", default=os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"))
    parser.add_argument("--auth-header-env", default="NEPENTHES_OTLP_AUTH_HEADER")
    parser.add_argument("--timeout-seconds", type=positive_float, default=10.0)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--backoff-seconds", type=float, default=0.5)
    args = parser.parse_args(argv)
    if not args.endpoint:
        parser.error("provide --endpoint or OTEL_EXPORTER_OTLP_ENDPOINT")
    if args.max_retries < 0 or args.backoff_seconds < 0:
        parser.error("retry count and backoff must be non-negative")
    try:
        endpoint = validate_endpoint(args.endpoint)
        auth_header = os.environ.get(args.auth_header_env)
        report = send_directory(args.input_dir, endpoint, auth_header=auth_header,
                                timeout_seconds=args.timeout_seconds,
                                max_retries=args.max_retries,
                                backoff_seconds=args.backoff_seconds)
        output = args.input_dir / "otlp-transport-report.json"
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())