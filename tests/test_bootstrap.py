from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_project
import trust_policy


class BootstrapTests(unittest.TestCase):
    def test_owner_bootstrap_is_bound_to_security_commit(self):
        record = trust_policy.bootstrap()
        self.assertEqual(record["established_by"], "repository-owner")
        self.assertEqual(record["commit"], "f36d7ad350038c7c1089ca8da9b63feb663df292")
        self.assertEqual(record["autonomous_self_amendment"], "forbidden")

    def test_mandatory_critical_paths_cannot_be_removed(self):
        weakened = {"schema_version": 1, "authorities": {}, "critical": [], "high": [], "protected_outputs": []}
        with mock.patch.object(trust_policy, "load", return_value=weakened):
            trust_policy.policy.cache_clear()
            with self.assertRaisesRegex(ValueError, "missing mandatory critical"):
                trust_policy.policy()
        trust_policy.policy.cache_clear()

    def test_audit_reports_matching_promotion_digests(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / ".recursive-codex" / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "last-promotion.json").write_text(json.dumps({
                "candidate_digest": "a" * 64, "real_digest": "a" * 64, "equal": True,
            }), encoding="utf-8")
            errors: list[str] = []
            receipt = audit_project._promotion_receipt(root, errors)
        self.assertTrue(receipt["equal"])
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
