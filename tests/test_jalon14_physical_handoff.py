from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_jalon14_audit_passes():
    result = subprocess.run(
        [sys.executable, "scripts/jalon14_audit.py"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "JALON14_PHYSICAL_HANDOFF_CLOSE=PASS" in result.stdout


def test_jalon14_reuses_canonical_execution_path():
    doc = (ROOT / "docs/jalones/jalon14.md").read_text(encoding="utf-8")
    assert "runtime-selection.v1" in doc
    assert "run_a01_selected.py" in doc
    assert "a01_runtime_benchmark.py" in doc
    assert "benchmark alternativo" in doc
    assert "segundo sistema de scoring" in doc
