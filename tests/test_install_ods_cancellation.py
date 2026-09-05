import pytest

pytest.importorskip(
    "runtime_selection.llmfit",
    reason="RC2 wizard/LLMFit path is historical and outside RC3",
)

import scripts.rc2_wizard as wizard
from scripts.rc2_i18n import set_language, tr
from scripts.rc2_wizard import WizardIO


def test_ods_cancellation_is_nonzero_and_not_success(monkeypatch):
    set_language("es")

    class Completed:
        returncode = 3

    monkeypatch.setattr(wizard, "_choose", lambda io, title, options: options[0])
    monkeypatch.setattr(wizard.subprocess, "run", lambda *args, **kwargs: Completed())

    output = []
    result = wizard._maybe_run_installer(
        WizardIO(input_fn=lambda _: "1", output_fn=output.append),
        wizard.STACKS["ODS"],
    )

    assert result["status"] == "installer_failed_or_cancelled"
    assert result["returncode"] == 3
    assert result["real_installation"] is False
    assert any(part in line for line in output for part in tr("installer_finished_fail").splitlines())


def test_ods_wrapper_uses_distinct_exit_code_for_cancelled_consent():
    script = (wizard.REPO_ROOT / "scripts" / "integrations" / "install_ods.sh").read_text(encoding="utf-8")
    assert 'echo "Installation cancelled."; exit 3' in script
