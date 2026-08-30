from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_jalon13_audit_passes():
    result = subprocess.run(
        [sys.executable, "scripts/jalon13_audit.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "JALON13_V1_READINESS_CLOSE=PASS" in result.stdout


def test_user_launcher_is_the_documented_entrypoint():
    launcher = ROOT / "scripts/run_leones_v1.sh"
    guide = ROOT / "docs/V1-USER-GUIDE.md"
    assert launcher.is_file()
    assert "run_leones_v1.sh" in guide.read_text()
    assert "scripts/leones_v1.py" in launcher.read_text()
