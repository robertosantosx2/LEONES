"""Privacy guards for NEPENTHES evidence metadata and command records."""

from __future__ import annotations

from urllib.parse import urlsplit


SENSITIVE_KEYS = {
    "api_key", "apikey", "access_token", "token", "secret", "password",
    "authorization", "cookie", "set_cookie", "prompt", "prompt_text",
    "generated_text", "completion", "response_text", "raw_payload",
    "headers", "request_body", "response_body",
}
SENSITIVE_FLAGS = (
    "--api-key", "--token", "--access-token", "--secret", "--password",
    "--authorization", "--header", "--cookie", "--prompt", "--prompt-file",
    "--input", "--input-file", "--completion", "--response", "--payload",
    "-p", "-f",
)


def assert_safe_metadata(value, path: str = "metadata") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in SENSITIVE_KEYS:
                raise ValueError(f"sensitive metadata key is not permitted: {path}.{key}")
            assert_safe_metadata(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_safe_metadata(child, f"{path}[{index}]")


def _safe_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<redacted-url>"
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return value
    host = parsed.hostname or ""
    if parsed.port:
        host += f":{parsed.port}"
    return f"{parsed.scheme}://{host}{parsed.path}"


def redact_command(command: list[str]) -> list[str]:
    redacted = []
    redact_next = False
    for raw in command:
        token = str(raw)
        if redact_next:
            redacted.append("<redacted>")
            redact_next = False
            continue
        matched = next((flag for flag in SENSITIVE_FLAGS if token == flag), None)
        if matched:
            redacted.append(token)
            redact_next = True
            continue
        matched_eq = next((flag for flag in SENSITIVE_FLAGS if token.startswith(flag + "=")), None)
        if matched_eq:
            redacted.append(matched_eq + "=<redacted>")
            continue
        redacted.append(_safe_url(token))
    if redact_next:
        redacted.append("<missing-sensitive-value>")
    return redacted
