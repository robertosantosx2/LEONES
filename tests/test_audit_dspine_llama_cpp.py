import tempfile
import unittest
from pathlib import Path

from audit_dspine_llama_cpp import audit


class DSpineAuditTests(unittest.TestCase):
    def make_tree(self, enum: str, implementation: str) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "common").mkdir()
        (root / "common/common.h").write_text(enum, encoding="utf-8")
        (root / "common/speculative.cpp").write_text(implementation, encoding="utf-8")
        return root

    def test_dflash_and_dspark_are_not_dspine(self):
        root = self.make_tree(
            "COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH, COMMON_SPECULATIVE_TYPE_DRAFT_DSPARK",
            ' { "draft-dflash", COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH },',
        )
        result = audit(root)
        self.assertEqual(result["status"], "NOT_IMPLEMENTED")
        self.assertFalse(result["checks"]["algorithm_enum"])
        self.assertFalse(result["checks"]["algorithm_name"])
        self.assertFalse(result["checks"]["runtime_implementation"])

    def test_all_explicit_markers_are_required(self):
        root = self.make_tree(
            "COMMON_SPECULATIVE_TYPE_DSPINE",
            ' { "draft-dspine", COMMON_SPECULATIVE_TYPE_DSPINE }; '
            "struct common_speculative_impl_draft_dspine {};",
        )
        result = audit(root)
        self.assertEqual(result["status"], "IMPLEMENTATION_MARKERS_PRESENT")
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
