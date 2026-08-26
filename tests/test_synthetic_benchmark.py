from benchmarks.synthetic_benchmark import run


def test_synthetic_benchmark_is_controlled_and_reproducible():
    first = run(iterations=10_000)
    second = run(iterations=10_000)

    assert first["schema"] == "synthetic-benchmark.v1"
    assert first["benchmark_type"] == "synthetic/controlled"
    assert first["iterations"] == 10_000
    assert first["result"] == second["result"]
    assert first["result_sha256"] == second["result_sha256"]
    assert first["wall_seconds"] >= 0
    assert first["measurement_scope"] == "CI synthetic workload only"


def test_synthetic_benchmark_never_presents_model_tps():
    result = run(iterations=100)
    assert "measured_tps" not in result
    assert "tokens_per_second" not in result
