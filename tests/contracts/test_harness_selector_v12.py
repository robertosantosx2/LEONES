import json
import unittest
from pathlib import Path


class HarnessSelectorV12Tests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).parents[2]
        self.data = json.loads((self.root / "web/data/harnesses.json").read_text(encoding="utf-8"))

    def test_selector_has_six_osi_candidates(self):
        candidates = self.data["candidates"]
        self.assertEqual(len(candidates), 6)
        self.assertTrue(all(c["osi"] for c in candidates))

    def test_ods_direct_install_is_not_overclaimed(self):
        direct = [c["name"] for c in self.data["candidates"] if c["ods"] == "DIRECT_INSTALL"]
        self.assertIn("Hermes Agent", direct)
        self.assertIn("OpenCode", direct)
        self.assertNotIn("OpenHands", direct)
        self.assertNotIn("DeepSeek Harness", direct)

    def test_magnitude_is_not_called_an_installer(self):
        text = self.data["compatibility_note"].lower()
        self.assertIn("no es instalador universal", text)
        self.assertIn("openai-compatible", text)

    def test_measurement_is_separate(self):
        self.assertEqual(self.data["measurement"], "not_measured")


if __name__ == "__main__":
    unittest.main()
