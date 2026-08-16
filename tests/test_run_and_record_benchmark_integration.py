#!/usr/bin/env python3
"""Prueba del recorrido completo con una salida simulada de llama.cpp.

No cuenta como benchmark de rendimiento: el proceso falso solo reproduce una
línea de salida con tok/s. Su objetivo es comprobar que adaptador, runner y
contrato de medición encajan entre sí antes de ejecutar un modelo real.
"""

from scripts.run_and_record_benchmark import run_and_record
from scripts.runtimes.llama_cpp_adapter import tokens_per_second_pattern


def test_llama_cpp_adapter_and_runner_form_complete_record():
    metadata = {
        "model": "integration-fixture",
        "variant": "Q4_K_M",
        "runtime": "llama.cpp",
        "hardware": "integration-test-host",
        "workload": "chat",
        "quantization": "Q4_K_M",
        "context_tokens": 4096,
    }
    result = run_and_record(
        ["python", "-c", "print('generation speed: 8.25 tok/s')"],
        metadata,
        tokens_per_second_pattern(),
    )
    assert result["measurement_type"] == "measured"
    assert result["runtime"] == "llama.cpp"
    assert result["tokens_per_second"] == 8.25
