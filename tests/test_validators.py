from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


import sys
sys.path.insert(0, str(ROOT / "scripts"))
validate_event = load_module("validate_event", ROOT / "scripts" / "validate_change_event.py")
validate_project = load_module("validate_project", ROOT / "scripts" / "validate_project.py")


class ValidatorTests(unittest.TestCase):
    def test_template_event_is_valid_proposal(self):
        self.assertEqual(validate_event.validate(ROOT / "templates" / "change-event.yaml"), [])

    def test_stabilized_event_requires_validation(self):
        text = (ROOT / "templates" / "change-event.yaml").read_text(encoding="utf-8")
        text = text.replace("status: proposed", "status: stabilized")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.yaml"
            path.write_text(text, encoding="utf-8")
            errors = validate_event.validate(path)
        self.assertTrue(any("passed validation" in error for error in errors))
    def test_real_event_mapping_lists_are_parsed(self):
        event = validate_event.load(ROOT / ".recursive-codex" / "events" / "0001-initial-implementation.yaml")
        self.assertEqual(event["changes"][0]["component"], "plugin")
        self.assertEqual(event["collective_findings"][0]["role"], "forward-test-reviewer")


    def test_minimal_example_project_is_valid(self):
        self.assertEqual(validate_project.validate(ROOT / "examples" / "minimal-project"), [])


if __name__ == "__main__":
    unittest.main()
