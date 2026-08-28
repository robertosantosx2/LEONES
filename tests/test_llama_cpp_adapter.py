import re

from scripts.runtimes.llama_cpp_adapter import (
    build_command,
    build_command_from_plan,
    tokens_per_second_pattern,
)


def test_build_command_keeps_arguments_separate():
    """The default form remains shell-free and preserves the historical shape."""
    assert build_command("llama-cli", "/models/example.gguf", "hola mundo") == [
        "llama-cli",
        "-m",
        "/models/example.gguf",
        "-p",
        "hola mundo",
    ]


def test_build_command_bounded_form_is_deterministic():
    """A measured run must bound context and generated tokens explicitly."""
    assert build_command(
        "llama-cli",
        "/models/example.gguf",
        "hola",
        context_tokens=2048,
        max_output_tokens=128,
    ) == [
        "llama-cli",
        "-m",
        "/models/example.gguf",
        "-p",
        "hola",
        "--simple-io",
        "--single-turn",
        "-c",
        "2048",
        "-n",
        "128",
    ]


def test_build_command_rejects_invalid_bounds():
    """Zero/negative limits cannot silently produce an unbounded run."""
    for kwargs in ({"context_tokens": 0}, {"max_output_tokens": 0}):
        try:
            build_command("llama-cli", "model.gguf", "hola", **kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid llama.cpp bound was accepted")


def test_build_command_from_authorized_plan():
    """The adapter accepts an authorized llama.cpp plan only."""
    plan = {
        "execution_authorized": True,
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
    }
    assert build_command_from_plan(
        plan,
        "/models/example.gguf",
        "hola",
        context_tokens=2048,
    )[-5:] == ["--single-turn", "-c", "2048", "-n", "128"]


def test_unauthorized_plan_is_rejected():
    plan = {
        "execution_authorized": False,
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
    }
    try:
        build_command_from_plan(plan, "/models/example.gguf", "hola")
    except ValueError as exc:
        assert "not authorized" in str(exc)
    else:
        raise AssertionError("unauthorized plan was accepted")


def test_other_runtime_is_rejected():
    plan = {
        "execution_authorized": True,
        "runtime": "vllm",
        "quantization": "Q4_K_M",
    }
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
