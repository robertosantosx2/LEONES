from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_nepenthes_llama_submodule import (  # noqa: E402
    EXPECTED_URL,
    SUBMODULE_PATH,
    validate_manifest,
)


class SubmoduleManifestTests(unittest.TestCase):
    def manifest(self) -> dict:
        return {
            "local_fork_repository": EXPECTED_URL,
            "leones_submodule_path": SUBMODULE_PATH,
            "leones_submodule_commit": "76f186df71a41abb3ee20fffedee31ca5dbc7d9f",
            "fork_head_commit": "9a080f44b503c64f66c84a6274b9d9ee5d5b09d5",
            "local_fork_status": "behind_upstream_pending_runtime_stack_rebase",
        }

    def test_fork_head_may_advance_independently_of_reviewed_gitlink(self) -> None:
        manifest = self.manifest()
        validate_manifest(manifest, manifest["leones_submodule_commit"])

    def test_gitlink_must_match_explicit_submodule_pin(self) -> None:
        manifest = self.manifest()
        with self.assertRaisesRegex(ValueError, "leones_submodule_commit"):
            validate_manifest(manifest, "9a080f44b503c64f66c84a6274b9d9ee5d5b09d5")

    def test_fork_head_must_be_a_full_sha(self) -> None:
        manifest = self.manifest()
        manifest["fork_head_commit"] = "9a080f44"
        with self.assertRaisesRegex(ValueError, "fork_head_commit"):
            validate_manifest(manifest, manifest["leones_submodule_commit"])


if __name__ == "__main__":
    unittest.main()
