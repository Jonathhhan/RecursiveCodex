from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "autopoietic_kernel", ROOT / "domains" / "autopoiesis" / "kernel.py"
)
kernel = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(kernel)


class AutopoieticKernelTests(unittest.TestCase):
    def operation(self, kind, identifier, **payload):
        return {"kind": kind, "id": identifier, **payload}

    def chain(self):
        return [
            self.operation("distinction-drawn", "f1", marked="system", unmarked="environment", indicated="marked"),
            self.operation("perturbation-recorded", "p1", source="review", signal="theory drift"),
            self.operation("state-of-affairs-configured", "w1", objects=["system", "goal"], relations=[["system", "selects", "goal"]]),
            self.operation("proposition-formed", "prop1", possible_state="w1", text="The system selects a goal.", picture=[
                {"element": "system", "object": "system"},
                {"element": "goal", "object": "goal"},
            ]),
            self.operation("observation-produced", "o1", perturbation="p1", form="f1", proposition="prop1", description="security dominates generation"),
            self.operation("tension-formed", "t1", observations=["o1"], expectation="operations produce further operations", discrepancy="goals are supplied externally", priority=90, level="strategic", requires=[]),
        ]

    def test_perturbation_cannot_directly_become_goal(self):
        state = kernel.replay(self.chain()[:4])
        self.assertEqual(kernel.derive_goal(state), {"status": "quiescent"})

    def test_unknown_observation_reference_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown perturbation"):
            kernel.replay([self.operation("observation-produced", "o1", perturbation="missing", form="missing", proposition="missing", description="x")])

    def test_open_tension_generates_deterministic_connection(self):
        state = kernel.replay(self.chain())
        first = kernel.derive_goal(state)
        second = kernel.derive_goal(state)
        self.assertEqual(first, second)
        self.assertEqual(first["origin"], {"kind": "autopoietic-tension", "id": "t1"})
        self.assertIn("goals are supplied externally", first["summary"])

    def test_recorded_goal_must_match_internal_derivation(self):
        state = kernel.replay(self.chain())
        goal = kernel.derive_goal(state)
        valid = self.operation("goal-generated", goal["id"], tension="t1", goal=goal)
        replayed = kernel.replay([*self.chain(), valid])
        self.assertEqual(replayed["tensions"]["t1"]["status"], "connected")
        invalid = self.operation("goal-generated", "invented", tension="t1", goal=goal)
        with self.assertRaisesRegex(ValueError, "internal derivation"):
            kernel.replay([*self.chain(), invalid])

    def test_generate_next_persists_operation_and_reaches_quiescence(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "autopoiesis.jsonl"
            for operation in self.chain():
                kernel.append_event(journal, operation.pop("kind"), operation)
            goal = kernel.generate_next(journal)
            self.assertTrue(goal["id"].startswith("connection-"))
            self.assertEqual(kernel.generate_next(journal), {"status": "quiescent"})

    def test_system_can_deliberately_defer_continuation(self):
        events = [
            *self.chain(),
            self.operation(
                "continuation-deferred", "d1", tension="t1",
                reason="further writing would only simulate movement",
            ),
        ]
        state = kernel.replay(events)
        self.assertEqual(state["tensions"]["t1"]["status"], "deferred")
        self.assertEqual(kernel.derive_goal(state), {"status": "quiescent"})

    def test_second_order_observations_condense_into_goal_structure(self):
        initial = self.chain()
        first_state = kernel.replay(initial)
        first_goal = kernel.derive_goal(first_state)
        generated = self.operation(
            "goal-generated", first_goal["id"], tension="t1", goal=first_goal
        )
        second_order = [
            self.operation(
                "selection-observed", "s1", goal=first_goal["id"],
                mode="reproduction", form="f1",
                description="selection repeated an established response",
            ),
            self.operation(
                "selection-observed", "s2", goal=first_goal["id"],
                mode="variation", form="f1",
                description="selection varied implementation but retained structure",
            ),
            self.operation(
                "expectation-condensed", "e1", observations=["s1", "s2"],
                expectation="prefer reorganizations when variations repeat",
            ),
            self.operation(
                "perturbation-recorded", "p2", source="outcome", signal="variation repeated",
            ),
            self.operation(
                "observation-produced", "o2", perturbation="p2",
                form="f1", proposition="prop1", description="the same distinction recurred",
            ),
            self.operation(
                "tension-formed", "t2", observations=["o2"],
                expectation="structures can change", discrepancy="variation remains local",
                priority=80, level="strategic", requires=[],
            ),
        ]
        state = kernel.replay([*initial, generated, *second_order])
        next_goal = kernel.derive_goal(state)
        self.assertEqual(next_goal["structural_expectations"], ["e1"])
        self.assertEqual(state["selection_observations"]["s1"]["mode"], "reproduction")

    def test_observation_requires_a_known_proposition(self):
        events = self.chain()[:4]
        with self.assertRaisesRegex(ValueError, "unknown proposition"):
            kernel.replay([*events, self.operation(
                "observation-produced", "o1", perturbation="p1", form="f1",
                proposition="missing", description="unsupported picture",
            )])

    def test_proposition_can_be_tested_against_evidence(self):
        events = [*self.chain()[:4], self.operation(
            "proposition-tested", "pt1", proposition="prop1",
            result="confirmed", evidence="journal contains a selected goal",
        )]
        state = kernel.replay(events)
        self.assertEqual(state["propositions"]["prop1"]["status"], "confirmed")
        self.assertEqual(state["proposition_tests"]["pt1"]["evidence"],
                         "journal contains a selected goal")

    def test_representation_limit_supports_deliberate_silence(self):
        state = kernel.replay([
            self.operation("representation-limit-observed", "l1",
                           subject="whether the workflow is conscious",
                           reason="no operational test is declared"),
            self.operation("silence-entered", "s1", limit="l1",
                           reason="do not convert metaphysics into a technical claim"),
        ])
        self.assertEqual(state["silences"]["s1"]["limit"], "l1")
        self.assertEqual(kernel.derive_goal(state), {"status": "quiescent"})


if __name__ == "__main__":
    unittest.main()
