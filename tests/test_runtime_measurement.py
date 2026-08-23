from benchmarks.evidence.runtime_measurement import build_measurement, extract_measured_tps


def test_extract_json_tps():
    assert extract_measured_tps('{"tokens_per_second": 14.9}') == 14.9


def test_extract_text_tps():
    assert extract_measured_tps('generation complete: 9.5 tok/s') == 9.5


def test_missing_measurement_is_null():
    assert extract_measured_tps('{"status":"ok"}') is None


def test_measurement_keeps_unknown_tps_null():
    value = build_measurement(elapsed_seconds=1.25, output='{"status":"ok"}', source='FreeToken')
    assert value["wall_seconds"] == 1.25
    assert value["measured_tps"] is None
    assert value["measurement_status"] == "runtime_value_not_reported"
