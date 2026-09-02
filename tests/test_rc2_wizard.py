import scripts.rc2_wizard as wizard
from scripts.rc2_i18n import set_language, tr
from scripts.rc2_wizard import WizardIO, run_wizard
from scripts.integrations.verify_physical import PhysicalVerification


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


def _pass_verification(stack="ods"):
    return PhysicalVerification(
        stack=stack,
        status="PASS",
        real_installation=True,
        checks={"ok": True},
        observed={"fixture": True},
        missing=[],
        message="fixture pass",
    )


def _fail_verification(stack="ods"):
    return PhysicalVerification(
        stack=stack,
        status="FAIL",
        real_installation=False,
        checks={"ok": False},
        observed={},
        missing=["fixture_missing"],
        message="fixture fail",
    )


def test_wizard_blocks_without_physical_pass(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _fail_verification(name))
    # language, model, stack, authorize, defer installer, do not retry verify
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "PHYSICAL_VERIFY_FAILED"
    assert any(tr("verify_fail") in line for line in output)
    assert session.snapshot()["gates"]["execution_authorized"] is False


def test_wizard_advances_only_after_physical_pass(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    answers = iter(["1", "1", "1", "1", "2"])  # defer installer, verify passes
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data["installation_verification"]["real_installation"] is True


def test_wizard_allows_magnitude_choice(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification("magnitude"))
    answers = iter(["1", "1", "2", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data["stack"]["name"] == "magnitude"
    assert any("install_magnitude.sh" in line for line in output)
