from pathlib import Path


def test_choice_flow_tui_exists_and_keeps_confirmation_separate():
    text = Path("scripts/rc4_choice_flow_tui.py").read_text()
    assert "PERSONAL AI ASSISTANT" in text
    assert "FULL SOHO" in text
    assert "BOTH" in text
    assert "CONFIRMACIÓN EXPLÍCITA" in text
    assert "authorized" not in text.lower()


def test_solution_catalog_declares_unknown_costs():
    text = Path("catalogs/rc4_solutions.json").read_text()
    assert '"disk_bytes": null' in text
    assert '"ram_bytes": null' in text
