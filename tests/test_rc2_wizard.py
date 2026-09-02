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
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "PHYSICAL_VERIFY_FAILED"
    assert any(tr("verify_fail") in line for line in output)


def test_wizard_can_decline_benchmark(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    # language, model, stack, authorize install, defer installer, decline A01
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data.get("benchmark_consent") == "declined"
    assert any(tr("a01_title") in line for line in output)
    assert any(tr("benchmark_declined") in line for line in output)
    assert session.snapshot()["gates"]["execution_authorized"] is False


def test_wizard_runs_a01_when_authorized(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    monkeypatch.setattr(
        wizard,
        "_run_a01",
        lambda io, model_choice, hardware: {
            "status": "benchmark_completed",
            "execution_id": "a01-fixture",
            "measured": True,
            "runtime_benchmark": {
                "execution_id": "a01-fixture",
                "wall_seconds": 1.2,
                "measured_tps": 3.4,
                "grader_pass": True,
                "measurement_status": "measured",
            },
        },
    )
    answers = iter(["1", "1", "1", "1", "2", "1"])  # authorize A01
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "COMPLETE"
    assert session.data["execution_id"] == "a01-fixture"
    assert session.data["benchmark_consent"] == "granted"
    assert session.snapshot()["gates"]["execution_authorized"] is True
