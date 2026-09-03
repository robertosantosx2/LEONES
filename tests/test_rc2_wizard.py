import scripts.rc2_wizard as wizard
from scripts.rc2_i18n import set_language, tr
from scripts.rc2_wizard import WizardIO, run_wizard
from scripts.integrations.verify_physical import PhysicalVerification
from scripts.a01_runtime_preflight import RuntimePreflight


HARDWARE = {
    "cpu": "fixture CPU", "ram_gb": 8, "gpu": None, "vram_gb": None,
    "os": "Linux", "architecture": "x86_64", "accelerators": [],
    "source": "fixture", "verification": "detected",
}
CANDIDATES = [{
    "model_id": "fixture-model", "name": "fixture-model", "rank": 1,
    "fit": "Perfect", "estimated_tps": 10.0, "source": "llmfit",
    "source_version": "fixture", "evidence_level": "estimated",
}]


def _pass_verification(stack="ods"):
    return PhysicalVerification(stack=stack, status="PASS", real_installation=True,
                                checks={"ok": True}, observed={"fixture": True},
                                missing=[], message="fixture pass")


def _fail_verification(stack="ods"):
    return PhysicalVerification(stack=stack, status="FAIL", real_installation=False,
                                checks={"ok": False}, observed={},
                                missing=["fixture_missing"], message="fixture fail")


def _available_model(model_id="fixture-model"):
    return RuntimePreflight(runtime="ollama", available=True, model_id=model_id,
                            model_available=True, installed_models=(model_id,))


def _output_contains_translation(output, key):
    """Assert every line of a possibly multiline translation was rendered."""
    return all(any(part in line for line in output) for part in tr(key).splitlines())


def test_wizard_blocks_without_physical_pass(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _fail_verification(name))
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "PHYSICAL_VERIFY_FAILED"
    assert _output_contains_translation(output, "verify_fail")


def test_wizard_blocks_a01_before_consent_when_model_unavailable(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    monkeypatch.setattr(wizard, "check_ollama_model", lambda model_id: RuntimePreflight(
        runtime="ollama", available=True, model_id=model_id, model_available=False,
        reason="model_not_installed_in_ollama", installed_models=("other-model",),
    ))
    # language, model, stack, authorize install, defer installer; there must be
    # no benchmark consent prompt because the runtime/model gate is closed.
    answers = iter(["1", "1", "1", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "A01_RUNTIME_UNAVAILABLE"
    assert session.data["benchmark_preflight"]["model_available"] is False
    assert session.data.get("benchmark_consent") is None
    assert _output_contains_translation(output, "benchmark_need_ollama")


def test_wizard_can_decline_benchmark(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    monkeypatch.setattr(wizard, "check_ollama_model", _available_model)
    # language, model, stack, authorize install, defer installer, decline A01
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data.get("benchmark_consent") == "declined"
    assert any(tr("a01_title") in line for line in output)
    assert _output_contains_translation(output, "benchmark_declined")
    assert session.snapshot()["gates"]["execution_authorized"] is False


def test_invalid_benchmark_choice_never_authorizes(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    monkeypatch.setattr(wizard, "check_ollama_model", _available_model)
    monkeypatch.setattr(wizard, "_run_a01", lambda *args, **kwargs: {
        "status": "benchmark_completed", "execution_id": "a01-fixture", "measured": True,
        "runtime_benchmark": {"execution_id": "a01-fixture", "wall_seconds": 1.2,
                               "measured_tps": 3.4, "grader_pass": True,
                               "measurement_status": "measured"},
    })
    # The invalid value must be rejected; only the following explicit 2 declines.
    answers = iter(["1", "1", "1", "1", "2", "bogus", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data["benchmark_consent"] == "declined"
    assert session.snapshot()["gates"]["execution_authorized"] is False
    assert _output_contains_translation(output, "invalid_option")


def test_wizard_runs_a01_when_authorized(monkeypatch):
    set_language("es")
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", lambda name: _pass_verification(name))
    monkeypatch.setattr(wizard, "check_ollama_model", _available_model)
    monkeypatch.setattr(wizard, "_run_a01", lambda io, model_choice, hardware: {
        "status": "benchmark_completed", "execution_id": "a01-fixture", "measured": True,
        "runtime_benchmark": {"execution_id": "a01-fixture", "wall_seconds": 1.2,
                               "measured_tps": 3.4, "grader_pass": True,
                               "measurement_status": "measured"},
    })
    answers = iter(["1", "1", "1", "1", "2", "1"])
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "COMPLETE"
    assert session.data["execution_id"] == "a01-fixture"
    assert session.data["benchmark_consent"] == "granted"
    assert session.snapshot()["gates"]["execution_authorized"] is True
