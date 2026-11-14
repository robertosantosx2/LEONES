import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import subprocess

from archive_NEPENTHES_evidence import collect_archive, evidence_files, sha256_file


class ArchiveEvidenceTests(unittest.TestCase):
    def init_repo(self, path):
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(path)], check=True, capture_output=True)
        return path

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
            repo = self.init_repo(root / "repo")
            archive_parent = repo / "artifacts"
            manifest = collect_archive(
                root, repo, [source], archive_parent, "test-run"
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
            repo = self.init_repo(root / "repo")
            manifest = collect_archive(
                root, repo, [first, second], root / "archive", "run"
            )
            self.assertEqual(manifest["copied_files"], 1)
            self.assertEqual(manifest["duplicate_files"], 1)

    def test_refuses_to_overwrite_existing_archive_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / "a.txt").write_text("x")
            repo = self.init_repo(root / "repo")
            archive = root / "archive"
            collect_archive(root, repo, [source], archive, "fixed")
            with self.assertRaises(FileExistsError):
                collect_archive(root, repo, [source], archive, "fixed")

    def test_skips_byte_identical_file_already_tracked_in_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self.init_repo(root / "repo")
            tracked = repo / "artifacts/benchmarks/tandem-qwen35-existing/existing.log"
            tracked.parent.mkdir(parents=True)
            tracked.write_text("same bytes")
            subprocess.run(["git", "-C", str(repo), "add", str(tracked)], check=True)
            source = root / "incoming"
            source.mkdir()
            (source / "copy.log").write_text("same bytes")
            manifest = collect_archive(
                root, repo, [source], repo / "artifacts/archive", "run"
            )
            self.assertEqual(manifest["copied_files"], 0)
            self.assertEqual(manifest["already_archived_files"], 1)
            self.assertEqual(manifest["files"][0]["status"], "already_archived_in_repo")
            self.assertFalse((repo / "artifacts/archive/run/incoming/copy.log").exists())


if __name__ == "__main__":
    unittest.main()
