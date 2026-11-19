from __future__ import annotations

import pytest

from scripts.nepenthes_privacy import assert_safe_metadata, redact_command


def test_redact_command_removes_prompt_credentials_and_url_query():
    command = [
        "llama-cli", "--prompt", "private prompt text",
        "--api-key=secret-value", "--url",
        "https://user:password@example.test/v1?token=do-not-leak",
        "--prompt-protocol-id", "nepenthes-c08-v1",
    ]
    redacted = redact_command(command)
    serialized = " ".join(redacted)
    for secret in ("private prompt text", "secret-value", "password", "do-not-leak"):
        assert secret not in serialized
    assert "--prompt-protocol-id" in serialized
    assert "nepenthes-c08-v1" in serialized


def test_sampling_metadata_rejects_sensitive_keys_recursively():
    assert_safe_metadata({"temperature": 0, "top_p": 1, "seed": 42})
    with pytest.raises(ValueError, match="sensitive metadata key"):
        assert_safe_metadata({"nested": {"api_key": "must-not-persist"}})
    with pytest.raises(ValueError, match="sensitive metadata key"):
        assert_safe_metadata({"authorization": "Bearer secret"})



def test_redact_command_hides_explicit_prompt_argument():
    assert redact_command(["llama-cli", "-p", "private prompt"], "private prompt") == [
        "llama-cli", "-p", "<redacted:prompt>"
    ]
