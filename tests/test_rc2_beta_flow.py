import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "rc2_beta.py"
FIXTURE = ROOT / "examples" / "rc1" / "real-a01-selection.json"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_rc2_bootstrap_without_side_effects():
    result = run("--stack", "ods", "--benchmark", "no")
    assert result.returncode == 0
    assert "RC2-A flow bootstrap: READY" in result.stdout
    assert "ODS capabilities:" in result.stdout
    assert "Magnitude capabilities:" in result.stdout


def test_rc2_bootstrap_can_load_selection_fixture():
    result = run("--selection", str(FIXTURE), "--stack", "magnitude", "--benchmark", "yes")
    assert result.returncode == 0
    assert "qwen2.5:0.5b-instruct-q4_K_M" in result.stdout
    assert "User choice: magnitude" in result.stdout
    assert "canonical runner/evidence path" in result.stdout


def test_selection_fixture_is_valid_json():
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    candidates = data.get("candidates")
    assert isinstance(candidates, list) and candidates
    assert candidates[0].get("model_id") == "qwen2.5:0.5b-instruct-q4_K_M"
