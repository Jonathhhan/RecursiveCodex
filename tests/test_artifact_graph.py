from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from artifact_graph import dependency_errors, ordered_artifacts


class ArtifactGraphTests(unittest.TestCase):
    def test_dependency_first_order_is_stable(self):
        artifacts = [
            {"id": "conclusion", "depends_on": ["premises"]},
            {"id": "premises"},
            {"id": "appendix"},
        ]
        self.assertEqual(
            [item["id"] for item in ordered_artifacts(artifacts)],
            ["premises", "conclusion", "appendix"],
        )

    def test_unknown_dependency_is_rejected(self):
        errors = dependency_errors([{"id": "text", "depends_on": ["missing"]}])
        self.assertIn(
            "artifacts[0].depends_on references unknown artifact: missing", errors
        )

    def test_cycle_reports_complete_path(self):
        errors = dependency_errors([
            {"id": "a", "depends_on": ["b"]},
            {"id": "b", "depends_on": ["a"]},
        ])
        self.assertIn("artifact dependency cycle: a -> b -> a", errors)


if __name__ == "__main__":
    unittest.main()
