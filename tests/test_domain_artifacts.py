from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "domain_artifacts", ROOT / "scripts" / "validate_domain_artifact.py"
)
validator = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(validator)


class DomainArtifactTests(unittest.TestCase):
    def test_language_artifact_preserves_selection_context(self):
        artifact = {
            "kind": "language", "text": "A sentence.", "audience": "readers",
            "register": "essay", "semantic_commitments": ["agency remains attributed"],
            "variants_considered": ["A sentence.", "The sentence."],
            "selection_reason": "preserves agency",
        }
        self.assertEqual(validator.validate(artifact, "language"), [])

    def test_logic_artifact_requires_explicit_countermodel_status(self):
        artifact = {
            "kind": "logic", "premises": ["P"], "conclusion": "P",
            "logic": "classical propositional logic", "derivation": ["premise P"],
            "countermodel_status": "unknown",
        }
        self.assertIn("countermodel_status is invalid", validator.validate(artifact, "logic"))

    def test_philosophical_objections_require_responses(self):
        artifact = {
            "kind": "philosophy", "thesis": "T", "concepts": ["T"],
            "reasons": ["R"], "objections": ["O1", "O2"], "responses": ["A1"],
            "sources": ["primary source"], "authority_status": "proposed",
        }
        self.assertIn(
            "every philosophical objection requires a response",

            validator.validate(artifact, "philosophy"),
        )
    def test_artifact_lists_require_non_empty_strings(self):
        artifact = {
            "kind": "logic", "premises": ["P", ""], "conclusion": "P",
            "logic": "classical logic", "derivation": ["premise P"],
            "countermodel_status": "not-found",
        }
        self.assertIn(
            "premises must be a non-empty list",
            validator.validate(artifact, "logic"),
        )

    def test_philosophical_responses_match_objections_one_to_one(self):
        artifact = {
            "kind": "philosophy", "thesis": "T", "concepts": ["C"],
            "reasons": ["R"], "objections": ["O"], "responses": ["A", "extra"],
            "sources": ["S"], "authority_status": "proposed",
        }
        self.assertIn("every philosophical objection requires a response", validator.validate(artifact, "philosophy"))

    def test_shipped_examples_are_valid(self):
        for kind in ("art", "language", "logic", "philosophy"):
            with self.subTest(kind=kind):
                data = json.loads(
                    (ROOT / "examples" / f"{kind}-artifact.json").read_text(encoding="utf-8")
                )
                self.assertEqual(validator.validate(data, kind), [])



if __name__ == "__main__":
    unittest.main()
