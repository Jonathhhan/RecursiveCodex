from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "autopoietic_bridge", ROOT / "domains" / "autopoiesis" / "bridge.py"
)
bridge = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(bridge)


class AutopoieticBridgeTests(unittest.TestCase):
    def create_goal(self, journal: Path) -> dict:
        bridge.autopoiesis.append_event(journal, "distinction-drawn", {
            "id": "f1", "marked": "system", "unmarked": "environment", "indicated": "marked",
        })
        bridge.autopoiesis.append_event(journal, "perturbation-recorded", {
            "id": "p1", "source": "review", "signal": "theory drift",
        })
        bridge.autopoiesis.append_event(journal, "state-of-affairs-configured", {
            "id": "w1", "objects": ["system", "goal"],
            "relations": [["system", "selects", "goal"]],
        })
        bridge.autopoiesis.append_event(journal, "proposition-formed", {
            "id": "prop1", "possible_state": "w1", "text": "The system selects a goal.",
            "picture": [{"element": "system", "object": "system"},
                        {"element": "goal", "object": "goal"}],
        })
        bridge.autopoiesis.append_event(journal, "observation-produced", {
            "id": "o1", "perturbation": "p1", "form": "f1", "proposition": "prop1",
            "description": "generation depends on external goals",
        })
        bridge.autopoiesis.append_event(journal, "tension-formed", {
            "id": "t1", "observations": ["o1"],
            "expectation": "operations reproduce operations",
            "discrepancy": "goals remain external", "priority": 90,
            "level": "strategic", "requires": [],
        })
        return bridge.autopoiesis.generate_next(journal)

    def test_export_is_hash_bound_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            goal = self.create_goal(auto)
            self.assertEqual(bridge.export_goals(auto, goals), [goal["id"]])
            self.assertEqual(bridge.export_goals(auto, goals), [])
            goal_events = bridge.read_journal(goals)
            self.assertEqual(len(goal_events), 1)
            operation = next(
                item for item in bridge.read_journal(auto)
                if item["kind"] == "goal-generated"
            )
            self.assertEqual(goal_events[0]["origin_operation_hash"], operation["event_hash"])
            state = bridge.autopoiesis.replay(bridge.read_journal(auto))
            self.assertEqual(state["generated_goals"][goal["id"]]["status"], "exported")

    def test_collision_with_unrelated_execution_goal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            goal = self.create_goal(auto)
            bridge.append_event(goals, "goal-added", {
                "id": goal["id"], "level": "strategic", "priority": 1,
                "requires": [], "origin_operation_hash": "0" * 64,
            })
            with self.assertRaisesRegex(ValueError, "goal collision"):
                bridge.export_goals(auto, goals)

    def test_execution_outcome_returns_only_as_perturbation(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            goal = self.create_goal(auto)
            bridge.export_goals(auto, goals)
            bridge.append_event(goals, "outcome-recorded", {
                "id": "result-1", "goal": goal["id"], "effect": "implemented bridge",
            })
            imported = bridge.import_outcomes(auto, goals)
            self.assertEqual(len(imported), 1)
            self.assertEqual(bridge.import_outcomes(auto, goals), [])
            state = bridge.autopoiesis.replay(bridge.read_journal(auto))
            perturbation = state["perturbations"][imported[0]]
            self.assertEqual(perturbation["status"], "unobserved")
            self.assertEqual(bridge.autopoiesis.derive_goal(state), {"status": "quiescent"})


if __name__ == "__main__":
    unittest.main()
