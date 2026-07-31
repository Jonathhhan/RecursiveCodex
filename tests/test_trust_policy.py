from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from trust_policy import paths_for, risk_for_paths


class TrustPolicyTests(unittest.TestCase):
    def test_all_enforcement_modules_are_critical(self):
        for path in (
            "scripts/audit_project.py", "scripts/artifact_graph.py",
            "scripts/validate_domain_artifact.py", "scripts/recursive_codex.py",
            "domains/autopoiesis/kernel.py", "domains/autopoiesis/bridge.py",
            "domains/autopoiesis/cycle.py", "domains/autopoiesis/forms.py",
            "domains/autopoiesis/propositions.py",
        ):
            self.assertEqual(risk_for_paths([path]), "critical", path)

    def test_manifest_protects_itself_and_enforcement_directories(self):
        protected = paths_for("protected_outputs")
        self.assertIn("config/trust-boundaries.yaml", protected)
        self.assertIn("scripts", protected)


if __name__ == "__main__":
    unittest.main()
