"""Minimal OpenAI-compatible inference boundary used by LEONES.

Design decision: keep this connector deliberately boring. ODS/Hermes and
Magnitude can both consume an OpenAI-compatible endpoint, so LEONES should
not maintain two inference protocols. This module performs transport and
normalization only; agent behavior, benchmarking, and evidence remain owned
by their respective contracts.

The implementation uses only the Python standard library. That keeps the
first physical integration dependency-light and makes the connector usable
before Ubuntu-specific runtime installation.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class OpenAICompatibleEndpoint:
    """Connection details for one OpenAI-compatible server."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ValueError("base_url must not be empty")
        if not self.model.strip():
            raise ValueError("model must not be empty")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @property
    def normalized_base_url(self) -> str:
        """Return the API base without a trailing slash."""
        return self.base_url.rstrip("/")


def _headers(endpoint: OpenAICompatibleEndpoint) -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if endpoint.api_key:
        headers["Authorization"] = f"Bearer {endpoint.api_key}"
    return headers


def _get_json(endpoint: OpenAICompatibleEndpoint, path: str) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(
        f"{endpoint.normalized_base_url}{path}",
        headers=_headers(endpoint),
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=endpoint.timeout_seconds) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI-compatible GET failed: HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI-compatible GET failed: {exc.reason}") from exc


def health(endpoint: OpenAICompatibleEndpoint) -> dict[str, Any]:
    """Check the canonical model-discovery endpoint and normalize its result."""
    started = datetime.now(timezone.utc).isoformat()
    status, payload = _get_json(endpoint, "/v1/models")
    return {
        "base_url": endpoint.normalized_base_url,
        "http_status": status,
        "models": payload.get("data", []),
        "checked_at": started,
    }


def list_models(endpoint: OpenAICompatibleEndpoint) -> list[dict[str, Any]]:
    """Return models advertised by the endpoint."""
    _, payload = _get_json(endpoint, "/v1/models")
    models = payload.get("data", [])
    if not isinstance(models, list):
        raise ValueError("OpenAI-compatible /v1/models response has non-list data")
    return models


def chat(
    endpoint: OpenAICompatibleEndpoint,
    messages: list[dict[str, str]],
    *,
    max_tokens: int = 128,
    temperature: float | None = None,
) -> dict[str, Any]:
    """Execute one non-streaming chat completion and normalize observations.

    No benchmark metric is calculated here. The connector records only what
    the endpoint observed/reported; LEONES measurement contracts remain the
    authority for physical performance claims.
    """
    if not messages:
        raise ValueError("messages must not be empty")
    if max_tokens < 1:
        raise ValueError("max_tokens must be positive")

    body: dict[str, Any] = {
        "model": endpoint.model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if temperature is not None:
        body["temperature"] = temperature

    request = urllib.request.Request(
        f"{endpoint.normalized_base_url}/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers=_headers(endpoint),
        method="POST",
    )
    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(request, timeout=endpoint.timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
            status = response.status
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI-compatible chat failed: HTTP {exc.code}: {body_text}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI-compatible chat failed: {exc.reason}") from exc

    finished_at = datetime.now(timezone.utc).isoformat()
    return {
        "provider_id": "openai-compatible",
        "base_url": endpoint.normalized_base_url,
        "model": endpoint.model,
        "request_id": payload.get("id"),
        "started_at": started_at,
        "finished_at": finished_at,
        "latency_seconds": time.monotonic() - started,
        "usage": payload.get("usage"),
        "response_status": status,
        "response": payload,
    }
