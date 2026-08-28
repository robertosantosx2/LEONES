from scripts.runtimes.llama_cpp_adapter import build_command
from scripts.runtimes.run_llama_cpp_selected import run_plan


def test_run_plan_rejects_unauthorized_before_execution(tmp_path):
    plan = {
        "execution_authorized": False,
        "runtime": "llama.cpp",
        "quantization": "Q4_K_M",
        "model_id": "example/model",
    }
    try:
        run_plan(plan, model_path=str(tmp_path / "model.gguf"), prompt="hola",
                 hardware="test", workload="chat", context_tokens=128,
                 executable="definitely-not-a-runtime")
    except ValueError as exc:
        assert "not authorized" in str(exc)
    else:
        raise AssertionError("unauthorized execution was attempted")


def test_llama_cpp_command_is_non_interactive_and_bounded():
    command = build_command("llama-cli", "model.gguf", "hola", context_tokens=128)
    assert command[:6] == ["llama-cli", "-m", "model.gguf", "-p", "hola", "--simple-io"]
    assert command[-4:] == ["-c", "128", "-n", "128"]


def test_llama_cpp_command_rejects_unbounded_output():
    try:
        build_command("llama-cli", "model.gguf", "hola", max_output_tokens=0)
    except ValueError as exc:
        assert "max_output_tokens must be positive" in str(exc)
    else:
        raise AssertionError("zero max_output_tokens was accepted")
