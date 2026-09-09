from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_installer_has_activity_and_component_progress():
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "run_component()" in text
    assert "actividad" in text
    assert "Instalación %d/%d" in text


def test_tui_runs_real_operations_through_visible_progress():
    text = (ROOT / "scripts" / "rc4_tui.py").read_text(encoding="utf-8")
    assert "run_operation(" in text
    assert "OperationProgress" in text
    assert "ACTIVIDAD RC4" in text
    assert "terminal_progress" in text


def test_uninstaller_exposes_noninteractive_and_dry_run_controls():
    text = (ROOT / "scripts" / "uninstall.sh").read_text(encoding="utf-8")
    assert "--yes" in text
    assert "--dry-run" in text
