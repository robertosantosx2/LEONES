from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "RC2-D-STACK-CHOICE-AND-PREP.md"


def test_rc2_d_contract_exists():
    assert DOC.exists()


def test_rc2_d_separates_stack_install_and_benchmark():
    text = DOC.read_text(encoding="utf-8")
    assert "stack elegido" in text
    assert "¿preparar/instalar?" in text
    assert "¿hacer benchmark?" in text
    assert "La instalación/preparación no equivale a benchmark." in text


def test_rc2_d_forbids_parallel_installers_and_estimate_promotion():
    text = DOC.read_text(encoding="utf-8")
    assert "No debe crear otro instalador de ODS ni otro instalador de Magnitude." in text
    assert "Tampoco debe tratar una recomendación o estimación de ODS/Magnitude como medición LEONES." in text
