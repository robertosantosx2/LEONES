import unittest
from pathlib import Path


class FitCrossValidationContractTests(unittest.TestCase):
    def test_cross_validation_document_exists(self):
        path = Path(__file__).parents[2] / "docs" / "sources" / "FIT-CROSS-VALIDATION-2026-08-25.md"
        self.assertTrue(path.exists())

    def test_external_estimators_are_explicitly_separated_from_measurement(self):
        path = Path(__file__).parents[2] / "docs" / "sources" / "FIT-CROSS-VALIDATION-2026-08-25.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("Ningún resultado externo se convierte directamente en `measurement`", text)
        self.assertIn("measured_*", text)
        self.assertIn("runtime-selection.v1", text)

    def test_disagreement_classes_exist(self):
        path = Path(__file__).parents[2] / "docs" / "sources" / "FIT-CROSS-VALIDATION-2026-08-25.md"
        text = path.read_text(encoding="utf-8")
        for label in (
            "AGREE_FIT",
            "AGREE_NO_FIT",
            "MEMORY_DISAGREEMENT",
            "FIT_DISAGREEMENT",
            "PERFORMANCE_DISAGREEMENT",
            "METHODOLOGY_GAP",
            "STALE_DATA",
        ):
            self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
