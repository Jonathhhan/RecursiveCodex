from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from _mini_yaml import load


class KnowledgeDomainProfileTests(unittest.TestCase):
    def test_art_language_logic_and_philosophy_profiles_are_operational(self):
        for domain in ("art", "language", "logic", "philosophy"):
            with self.subTest(domain=domain):
                profile = load(ROOT / "domains" / f"{domain}.yaml")
                self.assertEqual(profile["schema_version"], 1)
                self.assertEqual(profile["id"], domain)
                self.assertTrue(profile["validity_dimensions"])
                self.assertTrue(profile["operation_cycle"])
                self.assertEqual(profile["artifact_contract"]["kind"], domain)
                self.assertEqual(
                    profile["artifact_contract"]["validator"],
                    "scripts/validate_domain_artifact.py",
                )
                self.assertIsInstance(profile["checks"], list)

    def test_philosophy_keeps_truth_outside_validator_authority(self):
        profile = load(ROOT / "domains" / "philosophy.yaml")
        self.assertTrue(any(
            "does not establish philosophical truth" in limit
            for limit in profile["limits"]
        ))


if __name__ == "__main__":
    unittest.main()
