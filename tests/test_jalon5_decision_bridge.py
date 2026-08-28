from __future__ import annotations

from scripts.ods_magnitude_decision import build_decision


def test_external_signals_are_not_measurements() -> None:
    result = build_decision(
        workload={"id": "text-generation"},
        hardware={"id": "host-1", "ram_gb": 16},
        runtime={"id": "llama.cpp", "selection_status": "approved"},
        selector_status="BENCHMARK_REQUIRED",
        model_id="model-a",
        basis=["ods_magnitude_fit", "llmfit_estimate"],
        ods_magnitude={"product": "ODS", "version": "1", "evidence_type": "observed"},
        llmfit={"version": "x"},
    )
    assert result["sources"]["llmfit"]["estimate_only"] is True
    assert result["sources"]["ods_magnitude"]["evidence_type"] == "observed"
    assert result["decision"]["measured_performance_used"] is False


def test_measured_execution_requires_identity() -> None:
    try:
        build_decision(
            workload={"id": "text-generation"},
            hardware={"id": "host-1"},
            runtime={"id": "llama.cpp", "selection_status": "approved"},
            selector_status="SELECTED",
            model_id="model-a",
            basis=["validated_local_measurement"],
            benchmark_required=False,
            measured_performance_used=True,
        )
    except ValueError as exc:
        assert "execution_id" in str(exc)
    else:
        raise AssertionError("measured performance must require execution_id")


def test_candidate_can_require_physical_benchmark() -> None:
    result = build_decision(
        workload={"id": "text-generation"},
        hardware={"id": "host-1"},
        runtime={"id": "llama.cpp", "selection_status": "approved"},
        selector_status="BENCHMARK_REQUIRED",
        model_id="model-a",
        basis=["external_fit_only"],
    )
    assert result["decision"]["benchmark_required"] is True
    assert result["decision"]["status"] == "BENCHMARK_REQUIRED"
