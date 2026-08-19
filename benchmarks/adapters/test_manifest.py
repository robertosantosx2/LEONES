import tempfile
import unittest
from pathlib import Path

from manifest import build_manifest, write_manifest


class ManifestTests(unittest.TestCase):
    def test_manifest_is_versioned_and_has_digest(self):
        manifest = build_manifest("magnitude", "local", "1.0", config={"model": {"name": "test"}})
        self.assertEqual(manifest["schema_version"], "1.0")
        self.assertEqual(manifest["adapter"], "magnitude")
        self.assertEqual(len(manifest["config_digest"]), 64)

    def test_manifest_writes_json(self):
        manifest = build_manifest("ods", "local", "2.6.0")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            write_manifest(manifest, str(path))
            self.assertTrue(path.exists())
            self.assertIn('"schema_version": "1.0"', path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
