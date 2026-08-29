from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENTRYPOINT = ROOT / "scripts/leones_v1.py"
LAUNCHER = ROOT / "scripts/run_leones_v1.sh"
SCHEMA = ROOT / "schemas/leones-v1-preflight.v1.json"


def test_preflight_matches_its_contract() -> None:
    result = subprocess.run(
        [sys.executable, str(ENTRYPOINT), "preflight"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    contract = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert payload["schema"] == contract["properties"]["schema"]["const"]
    assert payload["status"] == "observed"
    assert "tokens_per_second" not in payload
    assert "estimated_tps" not in payload


def test_launcher_is_a_thin_user_facing_wrapper() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "scripts/leones_v1.py preflight --pretty" in text
    assert "llama-cli" not in text
    assert "ollama" not in text
