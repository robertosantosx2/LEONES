import helpers


def test_icd_measurements_are_partitioned_by_exact_configuration_and_workload(tmp_path, monkeypatch):
    monkeypatch.setattr(helpers, "_PERF_FILE", tmp_path / "model-performance.json")

    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 42.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_benchmark",
        configuration_id="config-a",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 18.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_benchmark",
        configuration_id="config-b",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    helpers.record_model_performance(
        "demo-model", "Test GPU", "nvidia", 99.0,
        model_id="demo-model",
        gguf="demo-model.gguf",
        context_length=4096,
        vram_total_mb=4096,
        source="local_metric",
    )

    icd = helpers.get_inference_configuration_measurements(
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    assert {item["configuration_id"] for item in icd} == {"config-a", "config-b"}
    assert all(item["evidence_type"] == "measured" for item in icd)
    assert {item["measured_tps"] for item in icd} == {42.0, 18.0}

    wrong_workload = helpers.get_inference_configuration_measurements(
        workload_id="dashboard-local-benchmark-v1:max_tokens=512",
    )
    assert wrong_workload == []

    model_level = helpers.get_model_performance_samples()
    assert len(model_level) == 1
    assert model_level[0]["tokens_per_second"] == 99.0
    assert all(not item.get("configuration_id") for item in model_level)

    exact = helpers.get_recorded_model_performance(
        "demo-model", "Test GPU", "nvidia",
        context_length=4096,
        gguf="demo-model.gguf",
        vram_total_mb=4096,
        configuration_id="config-a",
        workload_id="dashboard-local-benchmark-v1:max_tokens=128",
    )
    assert exact is not None
    assert exact["configuration_id"] == "config-a"
    assert exact["workload_id"] == "dashboard-local-benchmark-v1:max_tokens=128"
