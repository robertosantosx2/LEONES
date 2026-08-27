from pathlib import Path

from scripts.runtimes.run_ollama_physical import run_one


def test_ollama_runner_uses_server_metrics(monkeypatch):
    monkeypatch.setattr(
        "scripts.runtimes.run_ollama_physical.post_json",
        lambda *args, **kwargs: [{
            "done": True,
            "response": "hola",
            "eval_count": 40,
            "eval_duration": 2_000_000_000,
            "prompt_eval_count": 7,
            "prompt_eval_duration": 100_000_000,
            "total_duration": 2_500_000_000,
            "_client_ttft_ms": 80.0,
            "_client_total_ms": 90.0,
        }],
    )
    out = run_one("http://127.0.0.1:11434", "qwen2.5:0.5b-instruct-q4_K_M", "hola", context=2048,
                  temperature=0, top_p=1, seed=42, timeout=10)
    assert out["output_tokens"] == 40
    assert out["tokens_per_second"] == 20
    assert out["generation_time_ms"] == 2000
    assert out["total_time_ms"] == 2500
    assert out["ttft_ms"] == 80
    assert out["exit_code"] == 0


def test_runner_file_exists():
    assert Path("scripts/runtimes/run_ollama_physical.py").is_file()
