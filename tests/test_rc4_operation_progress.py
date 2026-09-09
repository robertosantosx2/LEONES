from runtime_selection.operation_progress import OperationPhase, OperationProgress, terminal_progress


def test_install_progress_is_determinate_when_total_is_known():
    p = OperationProgress("install", OperationPhase.INSTALLING, current=25, total=100)
    assert p.determinate
    assert p.percent == 25.0
    assert "25.0%" in p.render()
    assert "25/100" in p.render()


def test_unknown_total_still_reports_activity():
    p = OperationProgress("uninstall", OperationPhase.REMOVING)
    assert not p.determinate
    assert p.active
    rendered = p.render()
    assert "removing" in rendered
    assert "…" in rendered


def test_byte_progress_supports_downloads():
    p = OperationProgress(
        "install", OperationPhase.DOWNLOADING,
        current_bytes=50, total_bytes=200,
        rate_bytes_per_second=100, eta_seconds=1.5,
    )
    assert p.percent == 25.0
    assert "25.0%" in p.render()
    assert "100 B/s" in p.render()
    assert "ETA 2s" in p.render()


def test_terminal_states_are_explicit():
    ok = terminal_progress("install", True)
    fail = terminal_progress("uninstall", False)
    assert ok.phase is OperationPhase.COMPLETED
    assert fail.phase is OperationPhase.FAILED
    assert not ok.active
    assert not fail.active


def test_invalid_progress_cannot_be_silent_or_inconsistent():
    try:
        OperationProgress("install", OperationPhase.INSTALLING, current=101, total=100)
    except ValueError:
        pass
    else:
        raise AssertionError("inconsistent progress must be rejected")
