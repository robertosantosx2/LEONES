import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class IntegrationPreflightTests(unittest.TestCase):
    def run_script(self, name):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "integrations" / name)],
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout)

    def test_ods_preflight_is_json_and_read_only(self):
        payload = self.run_script("ods_preflight.py")
        self.assertEqual(payload["profile"], "ods-server")
        self.assertIn("os", payload)
        self.assertIn("ram_gb", payload)
        self.assertIn("ready", payload)

    def test_magnitude_preflight_is_json_and_read_only(self):
        payload = self.run_script("magnitude_preflight.py")
        self.assertEqual(payload["profile"], "magnitude-assistant")
        self.assertIn("node", payload)
        self.assertIn("npm", payload)
        self.assertIn("ready", payload)


if __name__ == "__main__":
    unittest.main()
