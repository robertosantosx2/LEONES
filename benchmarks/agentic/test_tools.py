import tempfile
import unittest
from pathlib import Path

from tools import Sandbox, SandboxViolation


class SandboxTests(unittest.TestCase):
    def test_write_read_and_list(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory))
            sandbox.write_text("data/a.txt", "hola")
            self.assertEqual(sandbox.read_text("data/a.txt"), "hola")
            self.assertEqual(sandbox.list_files(), ["data/a.txt"])

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory))
            with self.assertRaises(SandboxViolation):
                sandbox.path("../outside.txt")

    def test_shell_disabled_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory))
            with self.assertRaises(SandboxViolation):
                sandbox.shell(["python", "-c", "print('no')"])

    def test_shell_uses_sandbox_when_explicitly_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            sandbox = Sandbox(Path(directory), allow_shell=True)
            result = sandbox.shell(["python", "-c", "print('ok')"])
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), "ok")


if __name__ == "__main__":
    unittest.main()
