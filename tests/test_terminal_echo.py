from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_leones_restores_terminal_echo_before_wizard():
    script = (ROOT / "leones").read_text(encoding="utf-8")
    assert "stty echo echonl" in script
    assert "restore_tty" in script
    assert "trap restore_tty EXIT INT TERM" in script


def test_ods_installer_restores_terminal_echo():
    script = (ROOT / "scripts" / "integrations" / "install_ods.sh").read_text(encoding="utf-8")
    assert "stty echo echonl" in script
    assert "trap restore_tty EXIT INT TERM" in script
