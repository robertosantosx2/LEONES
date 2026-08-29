from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/run_leones_v1.sh"


def test_launcher_exists_and_uses_canonical_front_door() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "scripts/leones_v1.py preflight --pretty" in text
    assert "benchmark" in text.lower()
    assert "recommendation" not in text.lower() or "recommendation" in text.lower()


def test_launcher_produces_json_preflight() -> None:
    result = subprocess.run(
        ["bash", str(LAUNCHER)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert '"schema": "leones-v1-preflight.v1"' in result.stdout
    assert '"status": "observed"' in result.stdout
