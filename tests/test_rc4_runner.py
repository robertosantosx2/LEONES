from pathlib import Path

from scripts.rc4_runner import PURPOSES, RC2_WIZARD, choose_purposes, main


ROOT = Path(__file__).resolve().parents[1]


def test_rc4_runner_exposes_multiple_user_intent_choices():
    assert len(PURPOSES) >= 2
    assert {purpose for purpose, _ in PURPOSES} >= {
        "programming",
        "reasoning",
        "research",
        "general",
    }


def test_rc4_runner_rejects_empty_intent_and_accepts_multiple(monkeypatch):
    answers = iter(["", "1,2,2"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert choose_purposes() == ["programming", "reasoning"]


def test_default_launcher_points_to_rc4_runner():
    launcher = (ROOT / "leones").read_text(encoding="utf-8")
    assert 'python3 "$ROOT/scripts/rc4_runner.py"' in launcher
    assert '"--rc2"' in launcher


def test_rc2_switch_delegates_to_historical_wizard(monkeypatch):
    calls = []

    class Result:
        returncode = 0

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr("scripts.rc4_runner.subprocess.run", fake_run)
    assert main(["--rc2"]) == 0
    assert calls
    command, kwargs = calls[0]
    assert command == ["python", str(RC2_WIZARD)] or command == [__import__("sys").executable, str(RC2_WIZARD)]
    assert kwargs["cwd"] == ROOT
    assert kwargs["check"] is False
