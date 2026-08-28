#!/usr/bin/env python3
"""Test the llama.cpp runner with simulated runtime output."""

from types import SimpleNamespace

from scripts.runtimes import run_llama_cpp_selected as runner


def test_llama_cpp_runner_forms_complete_record(monkeypatch, tmp_path):
    plan = {
        "execution_authorized": True,
        "runtime": "llama.cpp",
        "model_id": "integration-fixture",
        "quantization": "Q4_K_M",
    }

    def fake_run(*args, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout="generation speed: 8.25 tok/s",
            stderr="",
        )

    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    result = runner.run_plan(
        plan,
        model_path=str(tmp_path / "model.gguf"),
        prompt="hola",
        hardware="integration-test-host",
        workload="chat",
        context_tokens=4096,
        executable="llama-cli",
    )
    assert result["measurement_type"] == "measured"
    assert result["runtime"] == "llama.cpp"
    assert result["tokens_per_second"] == 8.25
