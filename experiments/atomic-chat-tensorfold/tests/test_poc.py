"""Offline unit tests for the TensorFold Atomic Chat PoC helpers.

Run with: python3 -m unittest discover -s tests -v
No TensorFold process, model download, GPU allocation or third-party package is needed.
"""
from __future__ import annotations

import socket
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import poc  # noqa: E402


class TensorFoldPocTests(unittest.TestCase):
    def test_server_command_is_argv_and_loopback_only(self) -> None:
        command = poc.build_command("/models/example", 43123)
        self.assertEqual(command[1:3], ["serve", "/models/example"])
        self.assertIn("--host", command)
        self.assertEqual(command[command.index("--host") + 1], "127.0.0.1")
        self.assertEqual(command[command.index("--port") + 1], "43123")
        self.assertEqual(command[command.index("--parallel") + 1], "1")
        self.assertEqual(command[command.index("--backend") + 1], "cuda")
        self.assertIn("--no-update-check", command)
        self.assertIsInstance(command, list)

    def test_free_port_is_valid_tcp_port(self) -> None:
        port = poc.free_port()
        self.assertGreater(port, 0)
        self.assertLessEqual(port, 65535)

    @patch("poc.subprocess.run")
    def test_gpu_memory_probe_parses_mib(self, run) -> None:
        run.return_value.stdout = "3072\n"
        self.assertEqual(poc.gpu_free_memory_mib(), 3072)
        run.assert_called_once_with(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            check=True,
            text=True,
            capture_output=True,
            timeout=10,
        )

    @patch("poc.subprocess.run")
    def test_gpu_memory_probe_rejects_non_numeric_output(self, run) -> None:
        run.return_value.stdout = "N/A\n"
        with self.assertRaises(ValueError):
            poc.gpu_free_memory_mib()


if __name__ == "__main__":
    unittest.main()
