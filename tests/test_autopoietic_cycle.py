from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "autopoietic_cycle", ROOT / "domains" / "autopoiesis" / "cycle.py"
)
cycle = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(cycle)


class AutopoieticCycleTests(unittest.TestCase):
    def prepare(self, auto: Path) -> None:
        cycle.kernel.append_event(auto, "distinction-drawn", {
            "id": "f1", "marked": "system", "unmarked": "environment", "indicated": "marked",
        })
        cycle.kernel.append_event(auto, "perturbation-recorded", {
            "id": "p1", "source": "review", "signal": "theory drift",
        })
        cycle.kernel.append_event(auto, "state-of-affairs-configured", {
            "id": "w1", "objects": ["system", "goal"],
            "relations": [["system", "selects", "goal"]],
        })
        cycle.kernel.append_event(auto, "proposition-formed", {
            "id": "prop1", "possible_state": "w1", "text": "The system selects a goal.",
            "picture": [{"element": "system", "object": "system"},
                        {"element": "goal", "object": "goal"}],
        })
        cycle.kernel.append_event(auto, "observation-produced", {
            "id": "o1", "perturbation": "p1", "form": "f1", "proposition": "prop1",
            "description": "external goals dominate",
        })
        cycle.kernel.append_event(auto, "tension-formed", {
            "id": "t1", "observations": ["o1"],
            "expectation": "operations reproduce operations",
            "discrepancy": "goals remain external", "priority": 90,
            "level": "strategic", "requires": [],
        })

    def test_cycle_stops_at_execution_boundary_by_default(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            self.prepare(auto)
            result = cycle.run_cycle(auto, goals, ROOT)
            self.assertEqual(result["status"], "execution-ready")
            self.assertEqual(len(result["exported"]), 1)

    def test_controller_outcome_stops_at_observation_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            self.prepare(auto)

            def runner(command, **kwargs):
                selected = cycle.select_next(cycle.replay_goals(cycle.read_journal(goals)))
                cycle.kernel.append_event(goals, "outcome-recorded", {
                    "id": "result", "goal": selected["goal"]["id"],
                    "effect": "execution changed repository",
                })
                return subprocess.CompletedProcess(command, 0, "ok", "")

            result = cycle.run_cycle(
                auto, goals, ROOT, execute=True,
                controller_command=["controller"], runner=runner,
            )
            self.assertEqual(result["status"], "observation-required")
            self.assertEqual(len(result["perturbations"]), 1)

    def test_unobserved_input_prevents_new_goal_generation(self):
        with tempfile.TemporaryDirectory() as directory:
            auto = Path(directory) / "auto.jsonl"
            goals = Path(directory) / "goals.jsonl"
            cycle.kernel.append_event(auto, "perturbation-recorded", {
                "id": "p1", "source": "environment", "signal": "new input",
            })
            result = cycle.run_cycle(auto, goals, ROOT)
            self.assertEqual(result["status"], "observation-required")
            self.assertEqual(cycle.read_journal(goals), [])


if __name__ == "__main__":
    unittest.main()
