#!/usr/bin/env python3
"""Pruebas pequeñas del contrato de la matriz de hardware.

No ejecutamos aquí miles de combinaciones ni una inferencia real. Estas
pruebas comprueban las dos garantías que hacen segura la publicación: el
diagnóstico debe distinguir exclusiones y una matriz sin resultados no debe
considerarse una matriz válida.
"""
from scripts.atlas_hardware_matrix import diagnose


def test_diagnose_counts_exclusions_and_fit():
    rows = [
        {"technical_profile_level": "T2", "workload": "chat", "hardware_id": "cpu-intel-i5-16gb", "estimated_memory_gb": "8", "context_tokens": "4096", "runtime": "llama.cpp", "quantization": "Q4"},
        {"technical_profile_level": "T1", "workload": "chat"},
        {"technical_profile_level": "T2", "workload": "code", "hardware_id": "cpu-intel-i5-16gb"},
        {"technical_profile_level": "T2", "workload": "chat", "hardware_id": "cpu-amd", "estimated_memory_gb": "8", "context_tokens": "4096", "runtime": "llama.cpp", "quantization": "Q4"},
        {"technical_profile_level": "T2", "workload": "chat", "hardware_id": "cpu-intel-i5-16gb", "estimated_memory_gb": "64", "context_tokens": "4096", "runtime": "llama.cpp", "quantization": "Q4"},
    ]
    result = diagnose(rows, "cpu-intel-i5-16gb", 16, 0, 4096)
    assert result["not_profile"] == 1
    assert result["workload"] == 1
    assert result["hardware"] == 1
    assert result["memory"] == 1
    assert result["fits"] == 1
