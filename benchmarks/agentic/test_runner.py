import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.agentic.runner import RunConfig, Trace, build_result, execute_tool, write_result


class RunnerContractTests(unittest.TestCase):
    def test_trace_records_tool_call_and_result_without_arguments(self):
        trace = Trace()

        def read_file(path):
            return Path(path).read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("ok")
            filename = handle.name
        try:
            value = execute_tool(trace, "filesystem.read", read_file, path=filename)
        finally:
            Path(filename).unlink(missing_ok=True)

        self.assertEqual(value, "ok")
        self.assertEqual([event.type for event in trace.events], ["tool_call", "tool_result"])
        self.assertNotIn("path", trace.events[0].details)

    def test_tool_call_budget_is_enforced(self):
        trace = Trace()
        with self.assertRaises(RuntimeError):
            execute_tool(trace, "noop", lambda: None, tool_calls_so_far=1, max_tool_calls=1)
        self.assertEqual(trace.events[-1].status, "budget_exceeded")

    def test_invalid_event_type_is_rejected(self):
        with self.assertRaises(ValueError):
            Trace().add("not-a-real-event")

    def test_build_result_keeps_outcome_and_trajectory_separate(self):
        config = RunConfig("leones-agentic", "1", "A01-001", "1")
        trace = Trace()
        trace.add("model", name="test-model")
        result = build_result(
            config,
            trace,
            model={"name": "test-model"},
            hardware={"ram_gb": 16, "os": "test"},
            inference={},
            outcome={"status": "success", "score": 1},
            metrics={"tool_calls": 0},
        )
        self.assertEqual(result["agentic"]["outcome"]["status"], "success")
        self.assertEqual(result["agentic"]["trajectory"][0]["type"], "model")

    def test_write_result_is_valid_json(self):
        config = RunConfig("leones-agentic", "1", "A01-001", "1")
        result = build_result(
            config,
            Trace(),
            model={"name": "test-model"},
            hardware={"ram_gb": 16, "os": "test"},
            inference={},
            outcome={"status": "unknown"},
            metrics={},
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "result.json"
            write_result(result, str(path))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema_version"], "1.1")


if __name__ == "__main__":
    unittest.main()
