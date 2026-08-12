import hashlib

import pytest

from leones.model_source import ModelSource


def test_source_accepts_https_and_sha256():
    digest = hashlib.sha256(b"test").hexdigest()
    ModelSource("https://example.com/model.gguf", digest).validate()


def test_source_rejects_invalid_hash():
    with pytest.raises(ValueError):
        ModelSource("https://example.com/model.gguf", "bad").validate()


def test_source_rejects_non_http_url():
    with pytest.raises(ValueError):
        ModelSource("file:///tmp/model.gguf").validate()
