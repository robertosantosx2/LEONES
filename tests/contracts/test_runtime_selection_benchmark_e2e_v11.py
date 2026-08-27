import unittest

from benchmarks.evidence.runtime_selection_evidence import build_runtime_feedback
from benchmarks.runtime_benchmark import measure
from benchmarks.runtime_benchmark_fixture import run as fixture_run
from runtime_selection.contract import RuntimeSelectionPlan
from runtime_selection.llama_cpp import prepare
from runtime_selection.registry import build_default_registry


class RuntimeSelectionBenchmarkE2EContractTests(unittest.TestCase):
    def test_selection_adapter_fixture_benchmark_evidence_feedback(self):
        registry = build_default_registry()
        runtime = registry.get("llama.cpp")
        request = type("Request", (), {
            "model": {"format": "gguf", "quantization": "q4"},
            "hardware": {"accelerators": ["cpu"], "memory_gb": 7},
            "workload": {"execution_mode": "cpu"},
        })()
        match = runtime.match(request)
        self.assertTrue(match.compatible)

        plan = RuntimeSelectionPlan(
            runtime_id="llama.cpp",
            adapter_id="llama_cpp.v1",
            model_ref="fixture/model.gguf",
            capability_match=match,
        )
        spec = prepare(plan)
        observed = fixture_run(spec, tokens_generated=40, elapsed_seconds=4.0)
        measured = measure(observed)

        self.assertEqual(measured.measured_tps, 10.0)
        result = measured.to_result()
        feedback = build_runtime_feedback(result)

        self.assertEqual(feedback["evidence_type"], "measured")
        self.assertEqual(feedback["execution_id"], "fixture-exec-001")
        self.assertEqual(feedback["metrics"]["measured_tps"], 10.0)
        self.assertTrue(feedback["selector_feedback"]["usable_for_runtime_comparison"])
        self.assertTrue(feedback["selector_feedback"]["replace_estimate"])

    def test_benchmark_refuses_missing_execution_identity(self):
        with self.assertRaisesRegex(ValueError, "execution_id"):
            measure({
                "runtime_id": "llama.cpp",
                "model_ref": "fixture/model.gguf",
                "tokens_generated": 40,
                "elapsed_seconds": 4.0,
            })

    def test_benchmark_refuses_non_positive_observation(self):
        with self.assertRaisesRegex(ValueError, "positive"):
            measure({
                "execution_id": "fixture-exec-002",
                "runtime_id": "llama.cpp",
                "model_ref": "fixture/model.gguf",
                "tokens_generated": 0,
                "elapsed_seconds": 4.0,
            })

    def test_fixture_cannot_turn_selection_into_measurement_by_itself(self):
        registry = build_default_registry()
        runtime = registry.get("llama.cpp")
        self.assertNotIn("measured_tps", runtime.metadata)
        self.assertNotIn("tokens_per_second", runtime.metadata)


if __name__ == "__main__":
    unittest.main()
