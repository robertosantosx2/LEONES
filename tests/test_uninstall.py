import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "uninstall.sh"


def run_uninstall(*args, cwd=None):
    env = os.environ.copy()
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        cwd=cwd or REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def test_leones_cleanup_preserves_historical_evidence(tmp_path):
    (tmp_path / ".leones").mkdir()
    (tmp_path / ".leones" / "state.txt").write_text("temporary", encoding="utf-8")

    executions = tmp_path / "artifacts" / "runtime-executions"
    evidence = tmp_path / "artifacts" / "runtime-benchmark-evidence"
    executions.mkdir(parents=True)
    evidence.mkdir(parents=True)
    (executions / "execution.json").write_text("{}", encoding="utf-8")
    (evidence / "evidence.json").write_text("{}", encoding="utf-8")

    result = run_uninstall("--leones", "--yes", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / ".leones").exists()
    assert (executions / "execution.json").exists()
    assert (evidence / "evidence.json").exists()


def test_leones_dry_run_does_not_remove_state_or_evidence(tmp_path):
    (tmp_path / ".leones").mkdir()
    executions = tmp_path / "artifacts" / "runtime-executions"
    evidence = tmp_path / "artifacts" / "runtime-benchmark-evidence"
    executions.mkdir(parents=True)
    evidence.mkdir(parents=True)

    result = run_uninstall("--leones", "--dry-run", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".leones").exists()
    assert executions.exists()
    assert evidence.exists()
    assert "[DRY-RUN]" in result.stdout
