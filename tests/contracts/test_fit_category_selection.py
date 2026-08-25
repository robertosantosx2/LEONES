import unittest
from scripts.fit_consensus import CATEGORIES, SOURCES, reduce_estimator_outputs


def payload():
    result = {}
    for source_index, source in enumerate(SOURCES):
        candidates = []
        for category_index, category in enumerate(CATEGORIES):
            for n in range(6):
                candidates.append({
                    "model_id": f"{source}-{category}-{n}",
                    "category": category,
                    "parameters_m": (n + 1) * 1000 + source_index * 10 + category_index,
                    "is_moe": False,
                })
        result[source] = {"candidates": candidates}
    return result


class FitCategorySelectionTests(unittest.TestCase):
    def test_six_models_per_category_per_estimator(self):
        result = reduce_estimator_outputs(payload())
        self.assertEqual(result["required_per_estimator_per_category"], 6)
        self.assertEqual(result["expected_external_candidates"], 108)
        for source in SOURCES:
            self.assertTrue(result["validation"][source]["valid"])
            self.assertEqual(result["validation"][source]["categories"], {c: 6 for c in CATEGORIES})

    def test_selector_keeps_three_per_category(self):
        result = reduce_estimator_outputs(payload())
        self.assertEqual(result["selected_total"], 9)
        for category in CATEGORIES:
            selected = result["selected"][category]
            self.assertEqual(len(selected), 3)
            params = [x["selection_parameters_m"] for x in selected]
            self.assertEqual(params, sorted(params))
            self.assertEqual(params[0], min(params))
            self.assertEqual(params[-1], max(params))
            self.assertTrue(all(x["parameter_selection_basis"] == "total_parameters_m" for x in selected))

    def test_parameters_are_millions(self):
        result = reduce_estimator_outputs({
            SOURCES[0]: {"candidates": [
                {"model_id": "a", "category": "text", "parameters_b": 7},
                {"model_id": "b", "category": "text", "parameters_b": 8},
                {"model_id": "c", "category": "text", "parameters_b": 9},
                {"model_id": "d", "category": "text", "parameters_b": 10},
                {"model_id": "e", "category": "text", "parameters_b": 11},
                {"model_id": "f", "category": "text", "parameters_b": 12},
            ]}
        })
        self.assertEqual(result["validation"][SOURCES[0]]["candidates"]["text"][0]["total_parameters_m"], 7000)

    def test_moe_uses_active_parameters(self):
        candidates = []
        for i in range(6):
            candidates.append({"model_id": f"moe{i}", "category": "text", "parameters_b": 100 + i, "active_parameters_b": 5 + i, "is_moe": True})
        result = reduce_estimator_outputs({SOURCES[0]: {"candidates": candidates}})
        item = result["validation"][SOURCES[0]]["candidates"]["text"][0]
        self.assertEqual(item["total_parameters_m"], 100000)
        self.assertEqual(item["active_parameters_m"], 5000)
        self.assertEqual(item["selection_parameters_m"], 5000)
        self.assertEqual(item["parameter_selection_basis"], "active_parameters_m")

    def test_moe_without_active_parameters_is_invalid(self):
        candidates = [{"model_id": f"moe{i}", "category": "text", "parameters_b": 100 + i, "is_moe": True} for i in range(6)]
        result = reduce_estimator_outputs({SOURCES[0]: {"candidates": candidates}})
        self.assertFalse(result["validation"][SOURCES[0]]["valid"])
        self.assertEqual(result["validation"][SOURCES[0]]["categories"]["text"], 0)

    def test_incomplete_category_is_not_filled(self):
        result = reduce_estimator_outputs({
            SOURCES[0]: {"candidates": [
                {"model_id": f"m{i}", "category": "text", "parameters_m": i + 1}
                for i in range(5)
            ]}
        })
        self.assertFalse(result["validation"][SOURCES[0]]["valid"])
        self.assertEqual(result["selected"]["text"], [])


if __name__ == "__main__":
    unittest.main()
