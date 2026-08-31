from scripts.rc2_wizard import WizardIO, run_wizard


def test_wizard_keeps_installation_side_effect_free():
    answers = iter(["1", "1"])
    output = []
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=output.append))
    assert session.state == "READY_FOR_INSTALL"
    assert session.data["stack"] == "ODS — stack local"
    assert session.snapshot()["gates"]["execution_authorized"] is False
    assert any("L E O N E S" in line for line in output)


def test_wizard_allows_magnitude_choice():
    answers = iter(["2", "2"])
    session = run_wizard(WizardIO(input_fn=lambda _: next(answers), output_fn=lambda _: None))
    assert session.state == "READY_FOR_INSTALL"
    assert session.data["stack"] == "Magnitude — agente/asistente"
