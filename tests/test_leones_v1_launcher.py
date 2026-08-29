from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/run_leones_v1.sh"


def test_launcher_exists_and_delegates_without_parallel_logic() -> None:
    text = LAUNCHER.read_text(encoding="utf-8")
    assert "scripts/leones_v1.py preflight --pretty" in text
    assert "tokens_per_second" not in text
    assert "estimated_tps" not in text
    assert "ranking_score" not in text


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
