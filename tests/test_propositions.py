from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "tractarian_propositions", ROOT / "domains" / "autopoiesis" / "propositions.py"
)
model = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(model)


class PropositionModelTests(unittest.TestCase):
    def test_state_is_relational_not_a_bag_of_objects(self):
        state = model.configure_state(
            ["controller", "goal"], [["controller", "selects", "goal"]]
        )
        self.assertEqual(state["relations"][0][1], "selects")

    def test_relation_endpoints_must_exist(self):
        with self.assertRaisesRegex(ValueError, "configured objects"):
            model.configure_state(["controller"], [["controller", "selects", "missing"]])

    def test_picture_must_map_all_objects_one_to_one(self):
        state = model.configure_state(["controller", "goal"], [])
        proposition = model.form_proposition(state, "The controller selects a goal.", [
            {"element": "controller", "object": "controller"},
            {"element": "goal", "object": "goal"},
        ])
        self.assertEqual(proposition["sense"], "articulated")
        with self.assertRaisesRegex(ValueError, "every configured object"):
            model.form_proposition(state, "Incomplete", [
                {"element": "controller", "object": "controller"},
            ])

    def test_truth_status_requires_evidence(self):
        self.assertEqual(
            model.test_result("undetermined", "no admissible check"),
            {"result": "undetermined", "evidence": "no admissible check"},
        )


if __name__ == "__main__":
    unittest.main()
