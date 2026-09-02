import scripts.rc2_wizard as wizard
from scripts.rc2_i18n import set_language, tr
from scripts.rc2_wizard import WizardIO, run_wizard


HARDWARE = {
    "cpu": "fixture CPU",
    "ram_gb": 8,
    "gpu": None,
    "vram_gb": None,
    "os": "Linux",
    "architecture": "x86_64",
    "accelerators": [],
    "source": "fixture",
    "verification": "detected",
}
CANDIDATES = [
    {
        "model_id": "fixture-model",
        "name": "fixture-model",
        "rank": 1,
        "fit": "Perfect",
        "estimated_tps": 10.0,
        "source": "llmfit",
        "source_version": "fixture",
        "evidence_level": "estimated",
    }
]


def test_wizard_keeps_installation_side_effect_free(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    # language=1 (es), model=1, stack=1 (ODS), install=1 (authorize)
    answers = iter(["1", "1", "1", "1"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "INSTALLING"
    assert session.data["ui_language"] == "es"
    assert session.data["stack"]["name"] == "ods"
    assert session.data["installation_consent"] == "granted"
    assert session.snapshot()["gates"]["execution_authorized"] is False
    assert any("L E O N E S" in line for line in output)
    assert any(tr("ods_summary") in line for line in output)
    # After language choice, UI must not dump all three languages at once.
    assert not any(line.startswith("EN │ ") for line in output)


def test_wizard_allows_magnitude_choice(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    # language=1 (es), model=1, stack=2 (Magnitude), install=1
    answers = iter(["1", "1", "2", "1"])
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "INSTALLING"
    assert session.data["stack"]["name"] == "magnitude"
    assert session.data["installation_consent"] == "granted"


def test_wizard_english_language_path(monkeypatch):
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    answers = iter(["2", "1", "1", "1"])  # English
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.data["ui_language"] == "en"
    assert any("CHOOSE YOUR MODEL" in line for line in output)
    assert any("local inference stack" in line for line in output)
