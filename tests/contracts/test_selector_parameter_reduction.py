import unittest

from scripts.fit_consensus import CATEGORIES, SOURCES, reduce_estimator_outputs


class SelectorParameterReductionTests(unittest.TestCase):
    def _payload(self):
        payload = {}
        for source in SOURCES:
            candidates = []
            for category in CATEGORIES:
                for model_id, parameters in (("7b", 7), ("8b", 8), ("13b", 13), ("34b", 34), ("70b", 70), ("120b", 120)):
                    candidates.append({
                        "model_id": f"{source}-{category}-{model_id}",
                        "category": category,
                        "parameters_b": parameters,
                    })
            payload[source] = {"candidates": candidates}
        return payload

    def test_each_estimator_must_return_six_per_category(self):
        result = reduce_estimator_outputs(self._payload())
        self.assertEqual(result["expected_external_candidates"], 108)
        self.assertEqual(result["required_per_estimator_per_category"], 6)
        for source in SOURCES:
            self.assertTrue(result["validation"][source]["valid"])
            self.assertEqual(result["validation"][source]["returned_candidates"], 18)
            self.assertEqual(result["validation"][source]["categories"], {category: 6 for category in CATEGORIES})

    def test_selector_keeps_smallest_middle_and_largest_per_category_in_millions(self):
        result = reduce_estimator_outputs(self._payload())
        self.assertEqual(result["selected_total"], 9)
        for category in CATEGORIES:
            selected = result["selected"][category]
            self.assertEqual(len(selected), 3)
            params = [item["selection_parameters_m"] for item in selected]
            self.assertEqual(params, sorted(params))
            self.assertEqual(params[0], 7000.0)
            self.assertEqual(params[-1], 120000.0)
            self.assertTrue(all(item["parameter_selection_basis"] == "total_parameters_m" for item in selected))

    def test_incomplete_estimator_is_not_filled(self):
        payload = self._payload()
        payload[SOURCES[0]]["candidates"] = [
            item for item in payload[SOURCES[0]]["candidates"] if item["category"] != CATEGORIES[0]
        ] + payload[SOURCES[0]]["candidates"][:5]
        result = reduce_estimator_outputs(payload)
        self.assertFalse(result["validation"][SOURCES[0]]["valid"])
        self.assertEqual(result["validation"][SOURCES[0]]["categories"][CATEGORIES[0]], 5)
        self.assertEqual(result["validation"][SOURCES[0]]["returned_candidates"], 17)


if __name__ == "__main__":
    unittest.main()
