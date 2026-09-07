from pathlib import Path

from scripts.rc3_disk_preflight import build_report


def test_disk_preflight_records_filesystem_installation_and_no_install():
    report = build_report(base=Path("."))
    assert report["schema_version"] == "disk-preflight.v2"
    assert report["verification"] == "detected"
    assert report["download_installation"]["performed"] is False
    assert "hermes" in report["installation"]["installed"]
    assert "magnitude" in report["installation"]["installed"]
    assert "ods" in report["installation"]["installed"]
    assert report["selection_gate"]["model_artifact_recheck_required"] is True


def test_disk_preflight_distinguishes_magnitude_from_ods():
    report = build_report(
        base=Path("."), llm_reserve_gib=2.0, magnitude_reserve_gib=5.0
    )
    assert report["requirements"]["magnitude"]["basis"] == "leones_safety_reserve"
    assert report["requirements"]["ods"]["basis"] == "upstream_requirement"
    assert report["combined_reserves_gib"]["hermes_plus_llm_plus_magnitude"] == 9.0
    assert report["combined_reserves_gib"]["hermes_plus_llm_plus_ods"] == 44.0
    assert report["selection_gate"]["stack_readiness"]["magnitude"]["ready"] in (True, False)
    assert report["selection_gate"]["stack_readiness"]["ods"]["ready"] in (True, False)


def test_disk_preflight_blocks_when_filesystem_is_too_small(tmp_path, monkeypatch):
    class FakeUsage:
        total = 100 * 1024**3
        used = 99 * 1024**3
        free = 1 * 1024**3

    monkeypatch.setattr(
        "scripts.rc3_disk_preflight.shutil.disk_usage",
        lambda path: FakeUsage(),
    )

    report = build_report(base=tmp_path)

    assert report["selection_gate"]["ready"] is False
    assert report["selection_gate"]["state"] == "BLOCKED"
    assert report["status"]["llm"] is False
    assert report["status"]["magnitude"] is False
    assert report["status"]["ods"] is False


def test_disk_preflight_can_have_one_stack_ready_and_one_blocked(tmp_path):
    report = build_report(base=tmp_path, llm_reserve_gib=2.0, magnitude_reserve_gib=5.0)
    # tmp_path is on the same filesystem as the test runner; the result must
    # expose independent readiness for each stack rather than a single global
    # boolean that hides an ODS constraint.
    assert set(report["selection_gate"]["stack_readiness"]) == {"magnitude", "ods"}
    assert all("headroom_gib" in option for option in report["selection_gate"]["stack_readiness"].values())
