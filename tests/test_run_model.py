import subprocess

import pytest

from leones.run_model import run


def test_run_model_builds_small_command(tmp_path, monkeypatch):
    model = tmp_path / "model.gguf"
    model.write_bytes(b"model")
    monkeypatch.setattr("leones.run_model.check", lambda _: "llama.cpp test")
    monkeypatch.setattr(
        "leones.run_model.subprocess.run",
        lambda command, **kwargs: subprocess.CompletedProcess(command, 0, "answer", ""),
    )
    assert run(model, "hello", max_tokens=7) == "answer"


def test_run_model_requires_local_file(tmp_path, monkeypatch):
    monkeypatch.setattr("leones.run_model.check", lambda _: "llama.cpp test")
    with pytest.raises(ValueError):
        run(tmp_path / "missing.gguf", "hello")
