from pathlib import Path

from scripts.rc3_disk_preflight import build_report


def test_disk_preflight_records_filesystem_and_no_install():
    report = build_report(base=Path("."))
    assert report["schema_version"] == "disk-preflight.v1"
    assert report["verification"] == "detected"
    assert report["download_installation"]["performed"] is False
    assert report["selection_gate"]["model_artifact_recheck_required"] is True


def test_disk_preflight_distinguishes_magnitude_from_ods():
    report = build_report(
        base=Path("."), llm_reserve_gib=2.0, magnitude_reserve_gib=5.0
    )
    assert report["requirements"]["magnitude"]["basis"] == "leones_safety_reserve"
    assert report["requirements"]["ods"]["basis"] == "upstream_requirement"
    assert report["combined_reserves_gib"]["hermes_plus_llm_plus_magnitude"] == 9.0
    assert report["combined_reserves_gib"]["hermes_plus_llm_plus_ods"] == 44.0


def test_disk_preflight_blocks_when_filesystem_is_too_small(tmp_path):
    report = build_report(base=tmp_path, llm_reserve_gib=10**6, magnitude_reserve_gib=10**6)
    assert report["selection_gate"]["ready"] is False
    assert report["status"]["llm"] is False
    assert report["status"]["magnitude"] is False
    assert report["status"]["ods"] is False
