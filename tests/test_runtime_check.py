import subprocess

import pytest

from leones.runtime_check import check


def test_check_uses_version(monkeypatch):
    monkeypatch.setattr("leones.runtime_check.shutil.which", lambda _: "/usr/bin/llama-cli")
    monkeypatch.setattr(
        "leones.runtime_check.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, "llama.cpp version test", ""),
    )
    assert check("llama-cli") == "llama.cpp version test"


def test_check_rejects_missing_runtime(monkeypatch):
    monkeypatch.setattr("leones.runtime_check.shutil.which", lambda _: None)
    with pytest.raises(RuntimeError):
        check("llama-cli")
