from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_project", ROOT / "scripts" / "audit_project.py"
)
audit = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(audit)


class ProjectAuditTests(unittest.TestCase):
    def test_repository_graph_has_no_hard_errors(self):
        report = audit.audit(ROOT)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["status"], "passed")
        self.assertGreaterEqual(report["counts"]["events"], 42)

    def test_cycle_detection_reports_complete_path(self):
        self.assertEqual(
            audit._cycle_errors({"a": "b", "b": "a"}),
            ["event baseline cycle: a -> b -> a"],
        )

    def test_duplicate_ids_are_rejected(self):
        errors: list[str] = []
        records = [
            (Path("one.yaml"), {"id": "same"}),
            (Path("two.yaml"), {"id": "same"}),
        ]
        audit._unique_ids(records, "event", errors)
        self.assertIn("duplicate event id same: one.yaml, two.yaml", errors)

    def test_audit_reports_legacy_baselines_as_warnings(self):
        report = audit.audit(ROOT)
        self.assertTrue(any(
            "uses legacy baseline" in warning for warning in report["warnings"]
        ))
        self.assertEqual(report["counts"]["events"], report["counts"]["event_ids"])
        self.assertEqual(report["counts"]["decisions"], report["counts"]["decision_ids"])


if __name__ == "__main__":

    unittest.main()
