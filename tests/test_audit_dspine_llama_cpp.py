import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_dspine_llama_cpp import audit


class DSpineAuditTests(unittest.TestCase):
    def make_tree(self, complete: bool) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        files = {
            "gguf-py/gguf/constants.py": (
                "DSPINE_CODEBOOK DSPINE_GATE DSPINE_PRED_GATE DSPINE_PREV DSPINE_READ DSPINE_WRITE"
                if complete else "DFLASH_ONLY"
            ),
            "gguf-py/gguf/tensor_mapping.py": (
                "selected_prefix_bridge.codebook selected_prefix_bridge.gate "
                "selected_prefix_bridge.read selected_prefix_bridge.write"
                if complete else "dflash"
            ),
            "src/models/dflash.cpp": (
                "dspine_codebook dspine_gate dspine_pred_gate dspine_prev dspine_read dspine_write "
                "build_dspine_write build_dspine_lattice "
                "cur = build_dspine_write build_dspine_lattice(*this"
                if complete else "build_dflash"
            ),
            "common/speculative.cpp": (
                "common_speculative_impl_draft_dflash llama_get_embeddings_nextn is_dflash2 "
                '"draft-dflash"'
                if complete else "common_speculative_impl_draft_simple"
            ),
            "common/common.h": (
                "COMMON_SPECULATIVE_TYPE_DRAFT_DFLASH"
                if complete else "COMMON_SPECULATIVE_TYPE_DRAFT_SIMPLE"
            ),
        }
        for relative, content in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_dflash_only_tree_is_not_misreported_as_dspine(self):
        result = audit(self.make_tree(False))
        self.assertEqual(result["status"], "INCOMPLETE_OR_UNCONFIRMED")
        self.assertFalse(any(result["checks"].values()))

    def test_dspine_graph_and_dflash_dispatch_are_required(self):
        result = audit(self.make_tree(True))
        self.assertEqual(result["status"], "DSPINE_STATIC_INTEGRATION_FOUND_VIA_DRAFT_DFLASH")
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
