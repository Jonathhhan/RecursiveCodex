import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("generative_kernel", ROOT / "scripts" / "generative_kernel.py")
kernel = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(kernel)


class GenerativeKernelTests(unittest.TestCase):
    def event(self, kind, **payload):
        return {"schema_version": 1, "kind": kind, "time": "test", **payload}

    def test_selects_priority_then_level_deterministically(self):
        state = kernel.replay([
            self.event("goal-added", id="operational", level="operational", priority=5, requires=[]),
            self.event("goal-added", id="strategic", level="strategic", priority=5, requires=[]),
        ])
        self.assertEqual(kernel.select_next(state)["goal"]["id"], "strategic")

    def test_missing_capability_blocks_goal(self):
        state = kernel.replay([self.event("goal-added", id="build", level="tactical", priority=1, requires=["runner"])])
        self.assertEqual(kernel.select_next(state), {"status": "blocked", "blocked": {"build": ["runner"]}})

    def test_available_capability_unblocks_goal(self):
        state = kernel.replay([
            self.event("goal-added", id="build", level="tactical", priority=1, requires=["runner"]),
            self.event("capability-recorded", id="runner", status="available"),
        ])
        self.assertEqual(kernel.select_next(state)["status"], "selected")

    def test_failed_attempt_is_preserved_for_selection(self):
        state = kernel.replay([
            self.event("goal-added", id="build", level="tactical", priority=1, requires=[]),
            self.event("attempt-recorded", goal="build", strategy="snapshot", status="failed", reason="lost history"),
        ])
        self.assertEqual(kernel.select_next(state)["failed_strategies"], [{"strategy": "snapshot", "reason": "lost history"}])

    def test_outcome_completes_goal_and_reaches_quiescence(self):
        state = kernel.replay([
            self.event("goal-added", id="build", level="strategic", priority=1, requires=[]),
            self.event("outcome-recorded", id="done", goal="build", effect="shipped"),
        ])
        self.assertEqual(kernel.select_next(state), {"status": "quiescent"})

    def test_journal_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            kernel.append_event(path, "goal-added", {"id": "g", "level": "strategic", "priority": 1, "requires": []})
            self.assertEqual(kernel.replay(kernel.read_journal(path))["goals"]["g"]["status"], "pending")

    def test_duplicate_goal_is_rejected(self):
        event = self.event("goal-added", id="g", level="strategic", priority=1, requires=[])
        with self.assertRaisesRegex(ValueError, "duplicate goal"):
            kernel.replay([event, event])

    def test_normative_goal_requires_discourse_event(self):
        event = self.event(
            "goal-added", id="norm", level="strategic", priority=1,
            requires=[], claim_kind="normative",
        )
        with self.assertRaisesRegex(ValueError, "requires a discourse_event"):
            kernel.replay([event])

    def test_stabilized_discourse_admits_normative_goal(self):
        path = ROOT / "examples" / "communicative-event.yaml"
        event = self.event(
            "goal-added", id="norm", level="strategic", priority=1,
            requires=[], claim_kind="normative",
            discourse_event=str(path), discourse_hash=kernel.discourse_content_hash(path),
        )
        state = kernel.replay([event])
        self.assertEqual(state["goals"]["norm"]["claim_kind"], "normative")
        self.assertEqual(state["goals"]["norm"]["discourse_hash"], event["discourse_hash"])

    def test_proposed_discourse_cannot_admit_normative_goal(self):
        source = (ROOT / "examples" / "communicative-event.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "proposed.yaml"
            path.write_text(source.replace("status: stabilized", "status: proposed", 1), encoding="utf-8")
            event = self.event(
                "goal-added", id="norm", level="strategic", priority=1,
                requires=[], claim_kind="normative", discourse_event=str(path),
                discourse_hash=kernel.discourse_content_hash(path),
            )
            with self.assertRaisesRegex(ValueError, "requires a stabilized discourse event"):
                kernel.replay([event])

    def test_revoked_discourse_cannot_admit_normative_goal(self):
        source = (ROOT / "examples" / "communicative-event.yaml").read_text(encoding="utf-8")
        source = source.replace(
            "  closure:\n",
            "  revocation:\n"
            "    status: revoked\n"
            "    reason: Later evidence invalidated the normative basis.\n"
            "    authority: discourse-accepted-authority\n"
            "  closure:\n",
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "revoked.yaml"
            path.write_text(source, encoding="utf-8")
            event = self.event(
                "goal-added", id="norm", level="strategic", priority=1,
                requires=[], claim_kind="normative", discourse_event=str(path),
                discourse_hash=kernel.discourse_content_hash(path),
            )
            with self.assertRaisesRegex(ValueError, "has been revoked"):
                kernel.replay([event])

    def test_modified_discourse_is_rejected_by_bound_hash(self):
        source = ROOT / "examples" / "communicative-event.yaml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "discourse.yaml"
            path.write_bytes(source.read_bytes())
            event = self.event(
                "goal-added", id="norm", level="strategic", priority=1,
                requires=[], claim_kind="normative", discourse_event=str(path),
                discourse_hash=kernel.discourse_content_hash(path),
            )
            path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "content hash mismatch"):
                kernel.replay([event])

    def test_technical_goal_preserves_existing_state_shape(self):
        event = self.event("goal-added", id="legacy", level="operational", priority=0, requires=[])
        state = kernel.replay([event])
        self.assertEqual(state["goals"]["legacy"], {
            "id": "legacy", "level": "operational", "priority": 0,
            "requires": [], "status": "pending",
        })

    def test_invalid_goal_claim_kind_is_rejected(self):
        event = self.event("goal-added", id="g", level="strategic", priority=1, requires=[], claim_kind="factual")
        with self.assertRaisesRegex(ValueError, "invalid goal claim kind"):
            kernel.replay([event])
