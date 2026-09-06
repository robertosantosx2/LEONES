from pathlib import Path

from scripts.rc4_runner import PURPOSES, choose_purposes


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
