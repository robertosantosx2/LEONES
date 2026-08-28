#!/usr/bin/env python3
"""Test the llama.cpp runner with a simulated runtime output."""

from scripts.runtimes.run_llama_cpp_selected import run_plan


def test_llama_cpp_runner_forms_complete_record(tmp_path):
    plan = {
        "execution_authorized": True,
        "runtime": "llama.cpp",
        "model_id": "integration-fixture",
        "quantization": "Q4_K_M",
    }
    result = run_plan(
        plan,
        model_path=str(tmp_path / "model.gguf"),
        prompt="hola",
        hardware="integration-test-host",
        workload="chat",
        context_tokens=4096,
        executable="llama-cli",
    )
    assert result["measurement_type"] == "measured"
