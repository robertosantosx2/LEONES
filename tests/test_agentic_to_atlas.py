from scripts.agentic_to_atlas import agentic_to_atlas


def test_measured_agentic_result_becomes_atlas_feed_record():
    result = {
        "evidence": {
            "evidence_type": "measured",
            "execution_id": "run-a01-1",
            "measured_at": "2026-08-21T00:00:00+00:00",
            "measurement_kind": "real",
        },
        "model": {"name": "demo", "revision": "r1"},
        "hardware": {"profile": "H1"},
        "inference": {"generation_tokens_per_second": 12.5},
        "agentic": {
            "benchmark_id": "LEONES-Agentic",
            "benchmark_version": "1.0",
            "task_id": "A01",
            "task_version": "1.0",
            "execution_id": "run-a01-1",
            "runtime": {"name": "smoke"},
            "outcome": {"status": "success", "score": 1.0},
            "metrics": {"tool_calls": 2, "tool_errors": 0, "recovery_count": 0},
        },
    }
    row = agentic_to_atlas(result)
    assert row["evidence_type"] == "measured"
    assert row["execution_id"] == "run-a01-1"
    assert row["agentic_score"] == 1.0
    assert row["tokens_per_second"] == 12.5


def test_reported_agentic_result_cannot_enter_measured_atlas_feed():
    result = {"evidence": {"evidence_type": "reported"}}
    try:
        agentic_to_atlas(result)
    except ValueError as exc:
        assert "measured" in str(exc)
    else:
        raise AssertionError("reported evidence entered measured Atlas feed")
