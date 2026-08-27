import json
import unittest

from benchmarks.agentic.adapters.llmserve_a01 import runtime_hardware
from scripts.a01_runtime_benchmark import promote_measured_hardware


class A01RuntimeHardwareTests(unittest.TestCase):
    def test_runtime_hardware_line_is_extracted(self):
        hardware = {"ram_gb": 31.2, "os": "Linux 6.x", "cpu": "Test CPU", "gpu": None}
        output = (
            '{"tool":"lookup_model","arguments":{"model_id":"m"}}\n'
            '{"tool":"write_report","arguments":{"path":"report.txt"}}\n'
            '{"measured_tps":47.98}\n'
            '{"leones_runtime_hardware":' + json.dumps(hardware) + '}\n'
        )
        self.assertEqual(runtime_hardware(output), hardware)

    def test_measured_hardware_replaces_placeholder_plan_hardware(self):
        hardware = {"ram_gb": 31.2, "os": "Linux 6.x", "cpu": "Test CPU"}
        result = {"hardware": hardware, "runtime_selection": {"execution_plans": [{"hardware": {"ram_gb": 0, "os": "unknown"}}]}}
        promote_measured_hardware(result)
        self.assertEqual(result["runtime_selection"]["execution_plans"][0]["hardware"], hardware)

    def test_missing_hardware_keeps_existing_plan(self):
        result = {"runtime_selection": {"execution_plans": [{"hardware": {"ram_gb": 0, "os": "unknown"}}]}}
        promote_measured_hardware(result)
        self.assertEqual(result["runtime_selection"]["execution_plans"][0]["hardware"]["ram_gb"], 0)


if __name__ == "__main__":
    unittest.main()
