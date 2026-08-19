import tempfile
import unittest
from pathlib import Path

from graders import grade_file_exists, grade_required_files, grade_text_equals


class GraderTests(unittest.TestCase):
    def test_file_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "ok.txt").write_text("ok", encoding="utf-8")
            self.assertEqual(grade_file_exists(root, "ok.txt").status, "success")
            self.assertEqual(grade_file_exists(root, "missing.txt").status, "failed")

    def test_text_equals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "answer.txt").write_text("42", encoding="utf-8")
            self.assertEqual(grade_text_equals(root, "answer.txt", "42").score, 1.0)
            self.assertEqual(grade_text_equals(root, "answer.txt", "43").score, 0.0)

    def test_required_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a").write_text("", encoding="utf-8")
            self.assertEqual(grade_required_files(root, ["a"]).status, "success")
            self.assertEqual(grade_required_files(root, ["a", "b"]).status, "failed")


if __name__ == "__main__":
    unittest.main()
