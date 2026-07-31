from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from artifact_policy import resource_errors, validator_path


class ArtifactPolicyTests(unittest.TestCase):
    def test_registry_rejects_unknown_validator(self):
        with self.assertRaisesRegex(ValueError, "unregistered"):
            validator_path("arbitrary-path")

    def test_registry_resolves_installed_validator(self):
        self.assertEqual(validator_path("domain-artifact-v1").name, "validate_domain_artifact.py")

    def test_depth_and_size_are_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            large = root / "large.json"
            large.write_bytes(b"x" * (10 * 1024 * 1024 + 1))
            chain = [{"id": f"n{i}", "path": "small", "depends_on": [f"n{i-1}"] if i else []} for i in range(33)]
            chain.append({"id": "large", "path": "large.json"})
            errors = resource_errors(root, chain)
        self.assertIn("artifact graph exceeds max_dependency_depth", errors)
        self.assertTrue(any("max_artifact_bytes" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
