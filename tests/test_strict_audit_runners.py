from pathlib import Path
import stat

ROOT = Path(__file__).resolve().parents[1]
RUNNERS = [
    ROOT / "scripts/run_jalon3_audit.sh",
    ROOT / "scripts/run_jalon4_audit.sh",
    ROOT / "scripts/run_jalon5_audit.sh",
    ROOT / "scripts/run_jalon5_bridge_audit.sh",
    ROOT / "scripts/run_jalon6_audit.sh",
    ROOT / "scripts/run_jalon7_audit.sh",
    ROOT / "scripts/run_jalon8_audit.sh",
    ROOT / "scripts/run_jalon10_audit.sh",
    ROOT / "scripts/run_jalon11_audit.sh",
]


def test_all_declared_strict_runners_are_executable() -> None:
    missing = [str(path.relative_to(ROOT)) for path in RUNNERS if not path.is_file()]
    assert not missing, f"missing runner(s): {missing}"
    non_executable = [
        str(path.relative_to(ROOT))
        for path in RUNNERS
        if not (path.stat().st_mode & stat.S_IXUSR)
    ]
    assert not non_executable, f"runner(s) without executable bit: {non_executable}"


def test_tracked_audit_snapshots_are_written_after_output_capture_stops() -> None:
    for path in RUNNERS:
        text = path.read_text(encoding="utf-8")
        if "TRACKED_OUT=" not in text:
            continue
        assert 'tee "$TRACKED_OUT"' not in text, path.name
        assert "exec 3>&1 4>&2" in text, path.name
        assert "exec 1>&3 2>&4" in text, path.name
        assert 'cp "$OUT" "$TRACKED_OUT"' in text, path.name
