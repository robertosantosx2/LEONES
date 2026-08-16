#!/usr/bin/env python3
"""Pruebas del adaptador llama.cpp sin necesitar un modelo instalado."""

from scripts.runtimes.llama_cpp_adapter import build_command, tokens_per_second_pattern


def test_build_command_keeps_arguments_separate():
    command = build_command("llama-cli", "/models/example.gguf", "hola mundo")
    assert command == ["llama-cli", "-m", "/models/example.gguf", "-p", "hola mundo"]


def test_pattern_extracts_decimal_tok_per_second():
    import re
    match = re.search(tokens_per_second_pattern(), "generation speed: 12.5 tok/s")
    assert match
    assert float(match.group(1)) == 12.5
