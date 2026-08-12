import hashlib

import pytest

from leones.model_prepare import validate


def test_validate_gguf(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"model")
    digest = hashlib.sha256(b"model").hexdigest()
    validate(path, digest)


def test_validate_rejects_unknown_format(tmp_path):
    path = tmp_path / "model.xyz"
    path.write_bytes(b"model")
    with pytest.raises(ValueError):
        validate(path)


def test_validate_rejects_bad_hash(tmp_path):
    path = tmp_path / "model.gguf"
    path.write_bytes(b"model")
    with pytest.raises(ValueError):
        validate(path, "0" * 64)
