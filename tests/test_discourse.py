from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("validate_discourse", ROOT / "scripts" / "validate_discourse.py")
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(validator)


class DiscourseValidatorTests(unittest.TestCase):
    def test_valid_example(self):
        self.assertEqual(validator.validate(ROOT / "examples" / "communicative-event.yaml"), [])

    def _validate_modified(self, old: str, new: str):
        text = (ROOT / "examples" / "communicative-event.yaml").read_text(encoding="utf-8")
        self.assertIn(old, text)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.yaml"
            path.write_text(text.replace(old, new, 1), encoding="utf-8")
            return validator.validate(path)

    def test_stabilized_event_requires_all_affected_roles(self):
        errors = self._validate_modified("    - editor\n  claims:", "  claims:")
        self.assertTrue(any("excludes affected roles: editor" in error for error in errors))

    def test_unresolved_objection_blocks_stabilization(self):
        errors = self._validate_modified("status: addressed", "status: unresolved")
        self.assertIn("stabilized discourse cannot contain unresolved objections", errors)

    def test_addressed_objection_requires_response(self):
        errors = self._validate_modified(
            "      response: The distinction remains explicit in the revised second paragraph.\n",
            "",
        )
        self.assertTrue(any("requires a response" in error for error in errors))

    def test_nonaccepted_closure_blocks_stabilization(self):
        errors = self._validate_modified("    status: accepted\n    reason:", "    status: contested\n    reason:")
        self.assertIn("stabilized discourse requires accepted closure", errors)

    def test_revoked_discourse_retains_valid_historical_closure(self):
        errors = self._validate_modified(
            "  closure:\n",
            "  revocation:\n"
            "    status: revoked\n"
            "    reason: Later evidence invalidated the normative basis.\n"
            "    authority: discourse-accepted-authority\n"
            "  closure:\n",
        )
        self.assertEqual(errors, [])

    def test_revocation_requires_reason_and_authority(self):
        errors = self._validate_modified(
            "  closure:\n",
            "  revocation:\n"
            "    status: revoked\n"
            "  closure:\n",
        )
        self.assertIn("discourse revocation requires a reason", errors)
        self.assertIn("discourse revocation requires an authority", errors)


if __name__ == "__main__":
    unittest.main()
