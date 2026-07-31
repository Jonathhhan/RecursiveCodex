from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "run_autonomous_attestation", ROOT / "scripts" / "run_autonomous.py"
)
controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(controller)


class AutonomousAttestationTests(unittest.TestCase):
    PATCH = (
        "diff --git a/a.txt b/a.txt\n"
        "--- a/a.txt\n"
        "+++ b/a.txt\n"
        "diff --git a/.recursive-codex/events/0030-test.yaml b/.recursive-codex/events/0030-test.yaml\n"
        "--- /dev/null\n"
        "+++ b/.recursive-codex/events/0030-test.yaml\n"
        "diff --git a/.recursive-codex/decisions/0030-test.yaml b/.recursive-codex/decisions/0030-test.yaml\n"
        "--- /dev/null\n"
        "+++ b/.recursive-codex/decisions/0030-test.yaml\n"
    )

    def result(self):
        return {
            "status": "proposal",
            "summary": "test",
            "patch": self.PATCH,
            "selected_goal": "goal",
            "expected_paths": sorted(controller.patch_paths(self.PATCH)),
            "expected_checks": ["unit-tests"],
            "risk": "medium",
            "recovery": "Revert test.",
            "decision_id": "decision-test",
            "event_id": "test",
            "baseline_commit": "a" * 40,
            "workspace_digest": "b" * 64,
        }

    def test_exact_parent_attestation_is_accepted(self):
        errors = controller.proposal_attestation_errors(
            self.result(), "goal", [{"id": "unit-tests"}], "a" * 40, "b" * 64
        )
        self.assertEqual(errors, [])

    def test_mismatched_paths_checks_goal_and_baseline_are_rejected(self):
        result = self.result()
        result.update(
            selected_goal="other",
            expected_paths=[],
            expected_checks=[],
            baseline_commit="c" * 40,
            workspace_digest="d" * 64,
        )
        errors = controller.proposal_attestation_errors(
            result, "goal", [{"id": "unit-tests"}], "a" * 40, "b" * 64
        )
        self.assertEqual(len(errors), 5)

    def test_critical_risk_requires_external_authority(self):
        result = self.result()
        result["risk"] = "critical"
        errors = controller.proposal_attestation_errors(
            result, "goal", [{"id": "unit-tests"}], "a" * 40, "b" * 64
        )
        self.assertIn("critical proposals require external authority", errors)

    def test_record_ids_and_recovery_are_bound(self):
        result = self.result()
        errors = controller.record_attestation_errors(
            {"id": "test", "recovery": {"strategy": "Revert test."}},
            {"id": "decision-test"},
            result,
        )
        self.assertEqual(errors, [])
        result["event_id"] = "other"
        self.assertIn(
            "proposal event_id does not match change event",
            controller.record_attestation_errors(
                {"id": "test", "recovery": {"strategy": "Revert test."}},
                {"id": "decision-test"},
                result,
            ),
        )

    def test_workspace_digest_changes_with_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "state.txt"
            path.write_text("one", encoding="utf-8")
            first = controller.workspace_digest(root)
            path.write_text("two", encoding="utf-8")
            second = controller.workspace_digest(root)
        self.assertNotEqual(first, second)


if __name__ == "__main__":
    unittest.main()
