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
    # language=1 (es), model=1, stack=1 (ODS), install=1 (authorize), run installer=2 (no)
    answers = iter(["1", "1", "1", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "INSTALLING"
    assert session.data["ui_language"] == "es"
    assert session.data["stack"]["name"] == "ods"
    assert session.data["installation_consent"] == "granted"
    assert session.data["installation"]["installer"]["status"] == "deferred"
    assert session.data["installation"]["installer"]["real_installation"] is False
    assert session.snapshot()["gates"]["execution_authorized"] is False
    assert any("L E O N E S" in line for line in output)
    assert any(tr("ods_summary") in line for line in output)
    assert any(tr("not_installed_yet") in line for line in output)
    assert any("install_ods.sh" in line for line in output)
    assert not any(line.startswith("EN │ ") for line in output)


def test_wizard_allows_magnitude_choice(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    # language=1, model=1, stack=2 (Magnitude), authorize=1, defer installer=2
    answers = iter(["1", "1", "2", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "INSTALLING"
    assert session.data["stack"]["name"] == "magnitude"
    assert any("install_magnitude.sh" in line for line in output)


def test_wizard_english_language_path(monkeypatch):
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    answers = iter(["2", "1", "1", "1", "2"])  # English, defer installer
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.data["ui_language"] == "en"
    assert any("CHOOSE YOUR MODEL" in line for line in output)
    assert any("local inference stack" in line for line in output)
    assert any("Nothing has been installed" in line for line in output)
