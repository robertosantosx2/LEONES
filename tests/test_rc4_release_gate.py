"""RC4 release gate must PASS on the decision branch."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_rc4_release_gate_pass():
    script = ROOT / "scripts/rc4_release_gate.py"
    completed = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    assert "RC4 RELEASE GATE: PASS" in completed.stdout
