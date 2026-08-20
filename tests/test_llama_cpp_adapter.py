from scripts.runtimes.llama_cpp_adapter import build_command, build_command_from_plan, tokens_per_second_pattern
import re


def test_build_command_keeps_arguments_separate():
    assert build_command("llama-cli", "/models/example.gguf", "hola mundo") == [
        "llama-cli", "-m", "/models/example.gguf", "-p", "hola mundo"
    ]


def test_build_command_from_authorized_plan():
    plan = {"execution_authorized": True, "runtime": "llama.cpp", "quantization": "Q4_K_M"}
    assert build_command_from_plan(plan, "/models/example.gguf", "hola") == [
        "llama-cli", "-m", "/models/example.gguf", "-p", "hola"
    ]


def test_unauthorized_plan_is_rejected():
    plan = {"execution_authorized": False, "runtime": "llama.cpp", "quantization": "Q4_K_M"}
    try:
        build_command_from_plan(plan, "/models/example.gguf", "hola")
    except ValueError as exc:
        assert "not authorized" in str(exc)
    else:
        raise AssertionError("unauthorized plan was accepted")


def test_other_runtime_is_rejected():
    plan = {"execution_authorized": True, "runtime": "vllm", "quantization": "Q4_K_M"}
    try:
        build_command_from_plan(plan, "/models/example.gguf", "hola")
    except ValueError as exc:
        assert "unsupported runtime" in str(exc)
    else:
        raise AssertionError("wrong runtime was accepted")


def test_pattern_extracts_decimal_tok_per_second():
    match = re.search(tokens_per_second_pattern(), "generation speed: 12.5 tok/s")
    assert match
    assert float(match.group(1)) == 12.5
