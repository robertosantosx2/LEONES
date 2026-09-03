from scripts import llama_cpp_a01_runtime as runner


def test_find_llama_cli_prefers_llama_cli(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/llama-cli" if name == "llama-cli" else None)
    assert runner.find_llama_cli() == ["/usr/bin/llama-cli"]


def test_find_llama_cli_supports_new_llama_subcommand(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/llama" if name == "llama" else None)
    assert runner.find_llama_cli() == ["/usr/bin/llama", "cli"]


def test_main_builds_safe_hf_argv_with_bounded_context(monkeypatch):
    calls = []

    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/llama-cli" if name == "llama-cli" else None)
    monkeypatch.setattr(runner.subprocess, "run", lambda command, **kwargs: calls.append((command, kwargs)) or type("R", (), {"returncode": 0})())

    assert runner.main(["--model-ref", "hf://org/model-GGUF:Q4_1", "return JSONL"]) == 0
    command, kwargs = calls[0]
    assert command[:7] == [
        "/usr/bin/llama-cli", "-hf", "org/model-GGUF:Q4_1",
        "-c", "2048", "-p", "return JSONL",
    ]
    assert "return JSONL" in command
    assert kwargs == {"check": False, "shell": False}


def test_main_allows_explicit_context_and_threads(monkeypatch):
    calls = []

    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/llama-cli" if name == "llama-cli" else None)
    monkeypatch.setattr(runner.subprocess, "run", lambda command, **kwargs: calls.append(command) or type("R", (), {"returncode": 0})())

    assert runner.main([
        "--model-ref", "hf://org/model-GGUF:Q4_1",
        "--context", "1024", "--threads", "4", "--predict", "16", "prompt",
    ]) == 0
    assert calls[0] == [
        "/usr/bin/llama-cli", "-hf", "org/model-GGUF:Q4_1",
        "-c", "1024", "-p", "prompt", "-n", "16",
        "--no-display-prompt", "-t", "4",
    ]


def test_main_rejects_invalid_context(monkeypatch):
    monkeypatch.setattr(runner.shutil, "which", lambda name: "/usr/bin/llama-cli")
    try:
        runner.main(["--model-ref", "hf://org/model-GGUF:Q4_1", "--context", "0", "prompt"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("non-positive context must be rejected")


def test_main_rejects_non_hf_reference():
    try:
        runner.main(["--model-ref", "org/model-GGUF:Q4_1", "prompt"])
    except SystemExit as exc:
        assert exc.code != 0
    else:
        raise AssertionError("non-HF reference must be rejected")
