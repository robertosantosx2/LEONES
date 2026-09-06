import pytest

# RC2 wizard depends on the retired LLMFit adapter. RC2 remains historical;
# its tests are retained as audit material but are not part of RC3 collection.
pytest.importorskip(
    "runtime_selection.llmfit",
    reason="RC2 wizard/LLMFit path is historical and outside RC3",
)

import scripts.rc2_wizard as wizard
from scripts.rc2_i18n import set_language, tr
from scripts.rc2_wizard import WizardIO, run_wizard
from scripts.integrations.verify_physical import PhysicalVerification
from scripts.a01_runtime_preflight import RuntimePreflight


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
        "runtime": "ollama",
        "model_format": "Ollama-managed",
    }
]

OLLAMA_RESOLVED = {
    "schema_version": "model-runtime-resolution.v1",
    "status": "RESOLVED",
    "model_id": "fixture-model",
    "model_format": "Ollama-managed",
    "runtime_id": "ollama",
    "runtime_model_ref": "fixture-model",
    "reason": None,
}


def _pass_verification(stack="ods"):
    return PhysicalVerification(stack=stack, status="PASS", real_installation=True, checks={"ok": True}, observed={"fixture": True}, missing=[], message="fixture pass")


def _fail_verification(stack="ods"):
    return PhysicalVerification(stack=stack, status="FAIL", real_installation=False, checks={"ok": False}, observed={}, missing=["fixture_missing"], message="fixture fail")


def _available_model(model_id="fixture-model"):
    return RuntimePreflight(runtime="ollama", available=True, model_id=model_id, model_available=True, installed_models=(model_id,))


def _output_contains_translation(output, key):
    return all(any(part in line for line in output) for part in tr(key).splitlines())


def _patch_common(monkeypatch, *, verify, ollama=None, resolution=None, run_a01=None):
    monkeypatch.setattr(wizard, "_live_inputs", lambda io: (HARDWARE, CANDIDATES))
    monkeypatch.setattr(wizard, "verify_stack", verify)
    monkeypatch.setattr(wizard, "_resolve_for_benchmark", lambda model_choice: resolution or dict(OLLAMA_RESOLVED))
    if ollama is not None:
        monkeypatch.setattr(wizard, "check_ollama_model", ollama)
    if run_a01 is not None:
        monkeypatch.setattr(wizard, "_run_a01", run_a01)


def test_wizard_blocks_without_physical_pass(monkeypatch):
    set_language("es")
    _patch_common(monkeypatch, verify=lambda name: _fail_verification(name))
    answers = iter(["1", "1", "1", "1", "2", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "PHYSICAL_VERIFY_FAILED"
    assert _output_contains_translation(output, "verify_fail")


def test_wizard_blocks_a01_before_consent_when_model_unavailable(monkeypatch):
    set_language("es")

    def missing_model(model_id):
        return RuntimePreflight(runtime="ollama", available=True, model_id=model_id, model_available=False, reason="model_not_installed_in_ollama", installed_models=("other-model",))

    _patch_common(monkeypatch, verify=lambda name: _pass_verification(name), ollama=missing_model)
    answers = iter(["1", "1", "1", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "A01_RUNTIME_UNAVAILABLE"
    assert session.data["benchmark_preflight"]["model_available"] is False
    assert session.data.get("benchmark_consent") is None
    assert _output_contains_translation(output, "benchmark_need_ollama")


def test_wizard_blocks_when_runtime_unresolved(monkeypatch):
    set_language("es")
    unresolved = {"schema_version": "model-runtime-resolution.v1", "status": "UNRESOLVED", "model_id": "fixture-model", "model_format": None, "runtime_id": None, "runtime_model_ref": None, "reason": "no deterministic runtime mapping for model candidate"}
    _patch_common(monkeypatch, verify=lambda name: _pass_verification(name), resolution=unresolved)
    answers = iter(["1", "1", "1", "1", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "BLOCKED"
    assert session.error["code"] == "MODEL_RUNTIME_UNRESOLVED"
    assert session.data.get("benchmark_consent") is None
    assert _output_contains_translation(output, "runtime_unresolved")


def test_wizard_can_decline_benchmark(monkeypatch):
    set_language("es")
    _patch_common(monkeypatch, verify=lambda name: _pass_verification(name), ollama=_available_model)
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

    def fake_run(*args, **kwargs):
        return {"status": "benchmark_completed", "execution_id": "a01-fixture", "measured": True, "runtime_benchmark": {"execution_id": "a01-fixture", "wall_seconds": 1.2, "measured_tps": 3.4, "grader_pass": True, "measurement_status": "measured"}}

    _patch_common(monkeypatch, verify=lambda name: _pass_verification(name), ollama=_available_model, run_a01=fake_run)
    answers = iter(["1", "1", "1", "1", "2", "bogus", "2"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_BENCHMARK"
    assert session.data["benchmark_consent"] == "declined"
    assert session.snapshot()["gates"]["execution_authorized"] is False
    assert _output_contains_translation(output, "invalid_option")


def test_wizard_runs_a01_when_authorized(monkeypatch):
    set_language("es")

    def fake_run(io, *, model_choice, hardware, resolution):
        assert resolution["runtime_id"] == "ollama"
        return {"status": "benchmark_completed", "execution_id": "a01-fixture", "measured": True, "runtime_benchmark": {"execution_id": "a01-fixture", "wall_seconds": 1.2, "measured_tps": 3.4, "grader_pass": True, "measurement_status": "measured"}}

    _patch_common(monkeypatch, verify=lambda name: _pass_verification(name), ollama=_available_model, run_a01=fake_run)
    answers = iter(["1", "1", "1", "1", "2", "1"])
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "COMPLETE"
    assert session.data["execution_id"] == "a01-fixture"
    assert session.data["benchmark_consent"] == "granted"
    assert session.snapshot()["gates"]["execution_authorized"] is True
