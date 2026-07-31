import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("generate_hyperspace", ROOT / "scripts" / "generate_hyperspace.py")
hyperspace = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(hyperspace)


class HyperspaceTests(unittest.TestCase):
    def setUp(self):
        self.spec = {
            "dimensions": [
                {"id": "form", "options": [{"id": "open", "score": 2}, {"id": "fixed", "score": 1}]},
                {"id": "tempo", "options": [{"id": "slow"}, {"id": "fast", "score": 1}]},
                {"id": "response", "options": [{"id": "echo"}, {"id": "contrast", "score": 2}]},
            ]
        }

    def test_exhaustive_generates_cartesian_product(self):
        result = hyperspace.generate(self.spec, "exhaustive", 8)
        self.assertEqual(result["theoretical_size"], 8)
        self.assertEqual(len(result["possibilities"]), 8)

    def test_frontier_is_bounded_and_iterative(self):
        result = hyperspace.generate(self.spec, "frontier", 3)
        self.assertEqual([step["dimension"] for step in result["iterations"]], ["form", "tempo", "response"])
        self.assertTrue(all(step["retained"] <= 3 for step in result["iterations"]))
        self.assertEqual(len(result["possibilities"]), 3)

    def test_frontier_is_deterministic(self):
        self.assertEqual(hyperspace.generate(self.spec, max_nodes=3), hyperspace.generate(self.spec, max_nodes=3))

    def test_exhaustive_refuses_space_over_budget(self):
        with self.assertRaisesRegex(ValueError, "requires 8 nodes"):
            hyperspace.generate(self.spec, "exhaustive", 7)

    def test_rejects_duplicate_dimension(self):
        self.spec["dimensions"][1]["id"] = "form"
        with self.assertRaisesRegex(ValueError, "unique"):
            hyperspace.generate(self.spec)

    def test_exclusions_remove_incompatible_combinations(self):
        self.spec["exclusions"] = [{"form": "open", "tempo": "fast"}]
        result = hyperspace.generate(self.spec, "exhaustive", 8)
        self.assertEqual(len(result["possibilities"]), 6)
        self.assertEqual(result["iterations"][1]["excluded"], 1)
        self.assertTrue(
            all(
                node["choices"].get("form") != "open"
                or node["choices"].get("tempo") != "fast"
                for node in result["possibilities"]
            )
        )

    def test_exclusion_is_applied_when_its_dimensions_are_available(self):
        self.spec["exclusions"] = [{"form": "open", "response": "contrast"}]
        result = hyperspace.generate(self.spec, "frontier", 3)
        self.assertEqual(result["iterations"][0]["excluded"], 0)
        self.assertGreater(result["iterations"][2]["excluded"], 0)

    def test_rejects_unknown_exclusion_option(self):
        self.spec["exclusions"] = [{"tempo": "medium"}]
        with self.assertRaisesRegex(ValueError, "unknown option"):
            hyperspace.generate(self.spec)

    def test_conditional_exclusion_preserves_declared_exception(self):
        self.spec["exclusions"] = [
            {"when": {"form": "open"}, "unless": {"response": "echo"}}
        ]
        result = hyperspace.generate(self.spec, "exhaustive", 8)
        self.assertEqual(len(result["possibilities"]), 6)
        self.assertTrue(
            all(
                node["choices"]["form"] != "open"
                or node["choices"]["response"] == "echo"
                for node in result["possibilities"]
            )
        )

    def test_conditional_exclusion_waits_for_exception_dimension(self):
        self.spec["exclusions"] = [
            {"when": {"form": "open"}, "unless": {"response": "echo"}}
        ]
        result = hyperspace.generate(self.spec, "frontier", 8)
        self.assertEqual(result["iterations"][0]["excluded"], 0)
        self.assertEqual(result["iterations"][1]["excluded"], 0)
        self.assertGreater(result["iterations"][2]["excluded"], 0)

    def test_rejects_malformed_conditional_exclusion(self):
        self.spec["exclusions"] = [{"when": {"form": "open"}}]
        with self.assertRaisesRegex(ValueError, "only 'when' and 'unless'"):
            hyperspace.generate(self.spec)


if __name__ == "__main__":
    unittest.main()
