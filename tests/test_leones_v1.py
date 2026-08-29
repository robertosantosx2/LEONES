from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/leones_v1.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def test_preflight_is_machine_readable_and_does_not_measure() -> None:
    result = run_cli("preflight")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema"] == "leones-v1-preflight.v1"
    assert payload["status"] == "observed"
    assert "tokens_per_second" not in result.stdout
    assert "estimated_tps" not in result.stdout
    assert payload["contracts_present"]["recommendation"] is True
    assert payload["contracts_present"]["e2e_operation"] is True


def test_preflight_pretty_mode_is_still_json() -> None:
    result = run_cli("preflight", "--pretty")
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["note"].startswith("Preflight observes the host")


def test_cli_rejects_unknown_user_operation() -> None:
    result = run_cli("recommend")
    assert result.returncode != 0
