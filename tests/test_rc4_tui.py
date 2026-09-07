from pathlib import Path


def test_rc4_tui_exists_and_uses_curses():
    path = Path(__file__).parents[1] / "scripts" / "rc4_tui.py"
    text = path.read_text(encoding="utf-8")
    assert "import curses" in text
    assert "USER INTENT[]" in text
    assert "ESTIMATED" in text
    assert "local measurement boundary" in text


def test_tui_has_mandatory_multi_select_contract():
    path = Path(__file__).parents[1] / "scripts" / "rc4_tui.py"
    text = path.read_text(encoding="utf-8")
    assert "if not selected:" in text
    assert "run_recommendation" in text
    assert "SPACE select" in text
