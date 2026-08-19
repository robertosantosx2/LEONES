import tempfile
import unittest
from pathlib import Path

from runner import RunConfig, Trace, build_result, execute_tool, write_result


class RunnerContractTests(unittest.TestCase):
    def test_trace_records_tool_call_and_result(self):
        trace = Trace()

        def read_file(path):
            return Path(path).read_text(encoding="utf-8")

        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
            handle.write("ok")
            filename = handle.name
        try:
            value = execute_tool(trace, "filesystem.read", read_file, path=filename)
            self.assertEqual(value, "ok")
        finally:
            Path(filename).unlink(missing_ok=True)

        self.assertEqual([event.type for event in trace.events], ["tool_call", "tool_result"])

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

    def test_write_result(self):
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
            self.assertTrue(path.exists())
            self.assertIn('"agentic"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
