import unittest

from scripts.fit_consensus import SOURCES, reduce_estimator_outputs


class SelectorParameterReductionTests(unittest.TestCase):
    def _payload(self):
        payload = {}
        for source in SOURCES:
            payload[source] = {"candidates": [
                {"model_id": f"{source}-7b", "parameters_b": 7},
                {"model_id": f"{source}-8b", "parameters_b": 8},
                {"model_id": f"{source}-13b", "parameters_b": 13},
                {"model_id": f"{source}-34b", "parameters_b": 34},
                {"model_id": f"{source}-70b", "parameters_b": 70},
                {"model_id": f"{source}-120b", "parameters_b": 120},
            ]}
        return payload

    def test_each_estimator_must_return_six(self):
        result = reduce_estimator_outputs(self._payload())
        self.assertEqual(result["total_expected_candidates"], 36)
        for source in SOURCES:
            self.assertTrue(result["validation"][source]["valid"])
            self.assertEqual(result["validation"][source]["usable_candidates"], 6)

    def test_selector_keeps_smallest_middle_and_largest_in_millions(self):
        result = reduce_estimator_outputs(self._payload())
        self.assertEqual(result["selected_count"], 3)
        params = [item["parameters_m"] for item in result["selected"]]
        self.assertEqual(params, [7000.0, 34000.0, 120000.0])

    def test_incomplete_estimator_is_not_filled(self):
        payload = self._payload()
        payload[SOURCES[0]]["candidates"] = payload[SOURCES[0]]["candidates"][:5]
        result = reduce_estimator_outputs(payload)
        self.assertFalse(result["validation"][SOURCES[0]]["valid"])
        self.assertEqual(result["validation"][SOURCES[0]]["usable_candidates"], 5)


if __name__ == "__main__":
    unittest.main()
