"""Minimal OpenAI-compatible inference boundary used by LEONES.

ODS/Hermes and Magnitude can both consume an OpenAI-compatible endpoint, so
LEONES keeps one transport boundary instead of two inference protocols.
This module performs transport and normalization only; agent behavior,
benchmarking, and evidence remain owned by their respective contracts.

Only the Python standard library is used so the first physical integration
stays dependency-light and can be tested before Ubuntu-specific installation.
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
        """Normalize either a host URL or an already supplied `/v1` URL.

        ODS documentation commonly gives `http://host:8080/v1`, while other
        OpenAI-compatible clients conventionally store the host root. LEONES
        accepts both so configuration does not need a second URL convention.
        """
        value = self.base_url.rstrip("/")
        return value[:-3] if value.endswith("/v1") else value


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
    """Check `/v1/models` and normalize the observable result."""
    checked_at = datetime.now(timezone.utc).isoformat()
    status, payload = _get_json(endpoint, "/v1/models")
    return {
        "base_url": f"{endpoint.normalized_base_url}/v1",
        "http_status": status,
        "models": payload.get("data", []),
        "checked_at": checked_at,
    }


def list_models(endpoint: OpenAICompatibleEndpoint) -> list[dict[str, Any]]:
    """Return models advertised by `/v1/models`."""
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
    """Execute one non-streaming chat completion and preserve observations.

    No benchmark metric is invented here. Endpoint-reported usage and timing
    are observations; JALÓN 3 remains the authority for physical performance.
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

    return {
        "provider_id": "openai-compatible",
        "base_url": f"{endpoint.normalized_base_url}/v1",
        "model": endpoint.model,
        "request_id": payload.get("id"),
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "latency_seconds": time.monotonic() - started,
        "usage": payload.get("usage"),
        "response_status": status,
        "response": payload,
    }
