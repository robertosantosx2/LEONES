import unittest

from scripts.a01_runtime_benchmark import build_benchmark
from scripts.task_result import (
    aggregate_task_results,
    task_result_from_runtime_benchmark,
    validate_task_result,
)


def result(task_id, status, evidence=True):
    return {
        "schema_version": "task-result.v1",
        "task_id": task_id,
        "task_suite": "contract-suite",
        "task_revision": "1",
        "execution_id": f"exec-{task_id}",
        "benchmark_evidence_id": f"evidence-{task_id}" if evidence else None,
        "model_id": "example/model",
        "runtime": "llama.cpp",
        "hardware": {"cpu": "contract-cpu"},
        "workload": {"name": "contract"},
        "completion_status": status,
        "completion_score": 1.0 if status == "completed" else 0.0,
        "measurement_status": "MEASURED",
        "provenance": {"source": "contract-fixture"},
    }


def benchmark(evidence=True):
    return {
        "schema_version": "runtime-benchmark.v1",
        "execution_id": "exec-a01-001",
        "benchmark_evidence_id": "evidence-a01-001" if evidence else None,
        "runtime": "llama.cpp",
        "runtime_version": "1.0",
        "adapter": "llama.cpp.v1.1",
        "model_id": "example/model",
        "model_revision": "r1",
        "hardware": {"cpu": "contract-cpu"},
        "workload": {"name": "A01"},
        "measurement_status": "measured",
        "finished_at": "2026-08-29T12:00:00+00:00",
    }


def a01_result():
    return {
        "runtime_selection": {
            "execution_plans": [
                {
                    "runtime": {"name": "llama.cpp", "adapter": "llama.cpp.v1.1", "version": "1.0"},
                    "model": {"id": "example/model", "revision": "r1"},
                    "model_id": "example/model",
                    "quantization": "Q4_K_M",
                    "hardware": {"cpu": "contract-cpu"},
                    "workload": {"name": "A01"},
                    "estimated_tps": 10.0,
                }
            ]
        },
        "agentic": {
            "outcome": {"status": "success"},
            "metrics": {"runtime_wall_seconds": 2.0},
        },
    }


class Jalon7TaskResultTests(unittest.TestCase):
    def test_completed_requires_execution_evidence(self):
        errors = validate_task_result(result("t1", "completed", evidence=False))
        self.assertIn("completed task requires benchmark_evidence_id", errors)

    def test_failed_is_valid_but_not_completed(self):
        self.assertEqual(validate_task_result(result("t1", "failed")), [])

    def test_aggregation_is_deterministic_and_keeps_status_counts(self):
        summary = aggregate_task_results([
            result("t1", "completed"),
            result("t2", "failed"),
            result("t3", "not_evaluated"),
        ])
        self.assertEqual(summary["completed_tasks"], 1)
        self.assertEqual(summary["evaluated_tasks"], 2)
        self.assertEqual(summary["completion_rate"], 0.5)
        self.assertEqual(summary["counts"]["not_evaluated"], 1)
        self.assertEqual(summary["task_results"], ["t1", "t2", "t3"])
        self.assertEqual(summary["benchmark_evidence_ids"], ["evidence-t1", "evidence-t2"])

    def test_invalid_result_is_reported_not_repaired(self):
        bad = result("t1", "completed")
        bad["measurement_status"] = None
        bad["provenance"] = []
        summary = aggregate_task_results([bad])
        self.assertIn("t1", summary["invalid_contract"])
        self.assertIsNone(summary["completion_rate"])
        self.assertEqual(summary["completed_tasks"], 0)

    def test_measured_benchmark_projects_to_task_result(self):
        projected = task_result_from_runtime_benchmark(
            benchmark(),
            task_id="A01",
            task_suite="agentic-core",
            task_revision="1",
            completion_status="completed",
            completion_score=1.0,
        )
        self.assertEqual(projected["execution_id"], "exec-a01-001")
        self.assertEqual(projected["benchmark_evidence_id"], "evidence-a01-001")
        self.assertEqual(projected["measurement_status"], "measured")

    def test_projection_refuses_missing_execution_identity(self):
        bad = benchmark()
        del bad["execution_id"]
        with self.assertRaisesRegex(ValueError, "execution identity"):
            task_result_from_runtime_benchmark(
                bad,
                task_id="A01",
                task_suite="agentic-core",
                task_revision="1",
                completion_status="completed",
            )

    def test_a01_builder_emits_jalon7_traceability_fields(self):
        built = build_benchmark(
            {"candidates": []},
            a01_result(),
            "10 tokens/s",
            2.0,
            execution_id="exec-a01-builder",
            finished_at="2026-08-29T12:00:00+00:00",
        )
        self.assertEqual(built["schema_version"], "runtime-benchmark.v1")
        self.assertEqual(built["execution_id"], "exec-a01-builder")
        self.assertEqual(built["benchmark_evidence_id"], "A01:exec-a01-builder")
        self.assertEqual(built["measurement_status"], "measured")
        self.assertEqual(built["measured"]["tokens_per_second"], 10.0)


if __name__ == "__main__":
    unittest.main()
