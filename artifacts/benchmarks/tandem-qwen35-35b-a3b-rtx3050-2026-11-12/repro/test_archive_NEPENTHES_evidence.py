import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from archive_NEPENTHES_evidence import collect_archive, evidence_files, sha256_file


class ArchiveEvidenceTests(unittest.TestCase):
    def test_collects_evidence_and_excludes_model_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "NEPENTHES_TEST"
            source.mkdir()
            (source / "capture.sqlite").write_bytes(b"sqlite-evidence")
            (source / "server.log").write_text("server log\n")
            (source / "weights.gguf").write_bytes(b"model weights")
            cache = source / "models"
            cache.mkdir()
            (cache / "cache.json").write_text("{}")
            archive_parent = root / "repo" / "artifacts"
            manifest = collect_archive(
                root, root / "repo", [source], archive_parent, "test-run"
            )
            run_dir = archive_parent / "test-run"
            self.assertEqual(manifest["copied_files"], 2)
            self.assertFalse((run_dir / "NEPENTHES_TEST/weights.gguf").exists())
            self.assertFalse((run_dir / "NEPENTHES_TEST/models/cache.json").exists())
            self.assertEqual(
                sha256_file(run_dir / "NEPENTHES_TEST/capture.sqlite"),
                hashlib.sha256(b"sqlite-evidence").hexdigest(),
            )
            self.assertTrue((run_dir / "SHA256SUMS").is_file())
            saved = json.loads((run_dir / "ARCHIVE_MANIFEST.json").read_text())
            self.assertEqual(saved["copied_files"], 2)

    def test_duplicate_content_is_not_copied_twice(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = root / "first"
            second = root / "second"
            first.mkdir()
            second.mkdir()
            (first / "a.log").write_text("same")
            (second / "b.log").write_text("same")
            manifest = collect_archive(
                root, root / "repo", [first, second], root / "archive", "run"
            )
            self.assertEqual(manifest["copied_files"], 1)
            self.assertEqual(manifest["duplicate_files"], 1)

    def test_refuses_to_overwrite_existing_archive_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("x")
            archive = root / "archive"
            collect_archive(root, root / "repo", [source], archive, "fixed")
            with self.assertRaises(FileExistsError):
                collect_archive(root, root / "repo", [source], archive, "fixed")


if __name__ == "__main__":
    unittest.main()
