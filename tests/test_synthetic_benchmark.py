import unittest

from benchmarks.synthetic_benchmark import BENCHMARK_TYPE, ITERATIONS, SCHEMA, run


class SyntheticBenchmarkContractTests(unittest.TestCase):
    def test_default_run_is_deterministic_and_explicitly_synthetic(self):
        result = run()

        self.assertEqual(result["schema"], "synthetic-benchmark.v1")
        self.assertEqual(result["benchmark_type"], "synthetic/controlled")
        self.assertEqual(result["iterations"], ITERATIONS)
        self.assertEqual(result["result"], 685003)
        self.assertEqual(
            result["result_sha256"],
            "5d21dccb334081df664e4d2a9942ecec61716ed031f2063e6eb08cd0e04b78a2",
        )
        self.assertGreaterEqual(result["wall_seconds"], 0)
        self.assertEqual(
            result["measurement_scope"],
            "CI synthetic workload only",
        )

    def test_invalid_iteration_count_is_rejected(self):
        with self.assertRaises(ValueError):
            run(iterations=0)

    def test_schema_constants_match_serialized_contract(self):
        result = run(iterations=1)

        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["benchmark_type"], BENCHMARK_TYPE)


if __name__ == "__main__":
    unittest.main()
