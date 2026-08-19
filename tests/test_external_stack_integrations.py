import unittest

from scripts.integrations.external_stack import EvidenceResult, merge_evidence
from scripts.integrations.magnitude_adapter import MagnitudeAdapter
from scripts.integrations.ods_adapter import ODSAdapter


class ExternalStackIntegrationTests(unittest.TestCase):
    def test_ods_preflight_does_not_install(self):
        result = ODSAdapter("5a4450765976e2ad2792b9ac8927f4873dac60f6").preflight()
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.checks["install"], "not_run")

    def test_magnitude_preflight_does_not_install(self):
        result = MagnitudeAdapter("f6e1a090dbc8a46daed20e8e2f6b008d73a92532").preflight()
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.checks["install"], "not_run")

    def test_reported_evidence_is_not_promoted_to_measurement(self):
        evidence = EvidenceResult(state="REPORTED", product="ODS", model="example")
        result = merge_evidence({}, evidence)
        self.assertEqual(result["state"], "REPORTED")
        self.assertNotIn("tokens_per_second", result)


if __name__ == "__main__":
    unittest.main()
