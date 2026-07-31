from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


sys.path.insert(0, str(ROOT / "scripts"))
init_project = load_module("init_project", ROOT / "scripts" / "init_project.py")
mini_yaml = load_module("mini_yaml", ROOT / "scripts" / "_mini_yaml.py")
validate_event = load_module("validate_event", ROOT / "scripts" / "validate_change_event.py")
validate_project = load_module("validate_project", ROOT / "scripts" / "validate_project.py")


class EventValidatorTests(unittest.TestCase):
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

    def test_wrong_authority_type_is_reported_without_crashing(self):
        text = (ROOT / "templates" / "change-event.yaml").read_text(encoding="utf-8")
        original = "authority:\n  required: false\n  status: not_required\n  reference: null"
        self.assertIn(original, text, "template authority block changed")
        text = text.replace(original, "authority:\n  - invalid", 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.yaml"
            path.write_text(text, encoding="utf-8")
            errors = validate_event.validate(path)
        self.assertIn("authority must be a mapping", errors)

    def test_event_root_must_be_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.yaml"
            path.write_text("- item\n", encoding="utf-8")
            self.assertEqual(validate_event.validate(path), ["event must be a mapping"])


class MiniYamlTests(unittest.TestCase):
    def test_inline_empty_containers_keep_their_types(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "values.yaml"
            path.write_text("mapping: {}\nsequence: []\n", encoding="utf-8")
            data = mini_yaml.load(path)
        self.assertEqual(data["mapping"], {})
        self.assertEqual(data["sequence"], [])

    def test_nested_sequence_is_not_coerced_to_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "values.yaml"
            path.write_text("authority:\n  - invalid\n", encoding="utf-8")
            data = mini_yaml.load(path)
        self.assertEqual(data["authority"], ["invalid"])


class ProjectValidatorTests(unittest.TestCase):
    def test_minimal_example_project_is_valid(self):
        self.assertEqual(validate_project.validate(ROOT / "examples" / "minimal-project"), [])

    def test_missing_domain_profile_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(sys, "argv", ["init_project.py", str(root)]):
                self.assertEqual(init_project.main(), 0)
            (root / ".recursive-codex" / "domain.yaml").unlink()
            errors = validate_project.validate(root)
        self.assertTrue(any("invalid domain profile" in error for error in errors))

    def test_domain_profile_id_must_match_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(sys, "argv", ["init_project.py", str(root)]):
                self.assertEqual(init_project.main(), 0)
            profile = root / ".recursive-codex" / "domain.yaml"
            profile.write_text(
                profile.read_text(encoding="utf-8").replace(
                    "id: neutral", "id: research"
                ),
                encoding="utf-8",
            )
            errors = validate_project.validate(root)
        self.assertIn("domain profile id must match project domain", errors)

    def test_parent_traversal_path_is_rejected(self):
        template = (ROOT / "templates" / "project.yaml").read_text(encoding="utf-8")
        template = template.replace("events: .recursive-codex/events", "events: ../events")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".recursive-codex"
            target.mkdir()
            (target / "project.yaml").write_text(template, encoding="utf-8")
            errors = validate_project.validate(root)
        self.assertIn("paths.events must stay inside the project", errors)

    def test_missing_configured_directory_is_rejected(self):
        template = (ROOT / "templates" / "project.yaml").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".recursive-codex"
            target.mkdir()
            (target / "project.yaml").write_text(template, encoding="utf-8")
            errors = validate_project.validate(root)
        self.assertIn(
            "paths.events directory does not exist: .recursive-codex/events",
            errors,
        )
        self.assertIn(
            "paths.decisions directory does not exist: .recursive-codex/decisions",
            errors,
        )

    def test_protected_parent_traversal_is_rejected(self):
        template = (ROOT / "templates" / "project.yaml").read_text(encoding="utf-8")
        template = template.replace("protected: []", "protected:\n    - ../secrets")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".recursive-codex"
            target.mkdir()
            (target / "events").mkdir()
            (target / "decisions").mkdir()
            (target / "project.yaml").write_text(template, encoding="utf-8")
            errors = validate_project.validate(root)
        self.assertIn("paths.protected[0] must stay inside the project", errors)

    def test_checks_must_be_structured(self):
        template = (ROOT / "templates" / "project.yaml").read_text(encoding="utf-8")
        template = template.replace("checks: []", "checks:\n  - 42")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / ".recursive-codex"
            target.mkdir()
            (target / "project.yaml").write_text(template, encoding="utf-8")
            errors = validate_project.validate(root)
        self.assertIn("checks[0] must be a mapping", errors)
    def test_project_check_cannot_shadow_domain_check(self):
        declaration = (
            "checks:\n"
            "  - id: shared-check\n"
            "    command:\n"
            "      - python\n"
            "      - -m\n"
            "      - unittest\n"
            "    ephemeral_outputs: []"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(sys, "argv", ["init_project.py", str(root)]):
                self.assertEqual(init_project.main(), 0)
            contract = root / ".recursive-codex" / "project.yaml"
            contract.write_text(
                contract.read_text(encoding="utf-8").replace("checks: []", declaration),
                encoding="utf-8",
            )
            profile = root / ".recursive-codex" / "domain.yaml"
            profile.write_text(
                profile.read_text(encoding="utf-8").replace("checks: []", declaration),
                encoding="utf-8",
            )
            errors = validate_project.validate(root)
        self.assertIn("checks[0].id duplicates a domain profile check id", errors)

    def test_domain_output_cannot_overlap_project_protected_path(self):
        declaration = (
            "checks:\n"
            "  - id: domain-writer\n"
            "    command:\n"
            "      - python\n"
            "      - check.py\n"
            "    ephemeral_outputs:\n"
            "      - protected/domain-output.txt"
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with mock.patch.object(sys, "argv", ["init_project.py", str(root)]):
                self.assertEqual(init_project.main(), 0)
            contract = root / ".recursive-codex" / "project.yaml"
            contract.write_text(
                contract.read_text(encoding="utf-8").replace(
                    "protected: []", "protected:\n    - protected/domain-output.txt"
                ),
                encoding="utf-8",
            )
            profile = root / ".recursive-codex" / "domain.yaml"
            profile.write_text(
                profile.read_text(encoding="utf-8").replace("checks: []", declaration),
                encoding="utf-8",
            )
            errors = validate_project.validate(root)
        self.assertIn(
            "domain profile checks[0].ephemeral_outputs[0] overlaps protected state",
            errors,
        )



class InitializerTests(unittest.TestCase):
    def test_project_name_is_safely_quoted(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "null # project"
            project.mkdir()
            with mock.patch.object(sys, "argv", ["init_project.py", str(project)]):
                self.assertEqual(init_project.main(), 0)
            contract = project / ".recursive-codex" / "project.yaml"
            data = validate_project.load(contract)
            self.assertEqual(data["project"], "null # project")
            self.assertEqual(validate_project.validate(project), [])

    def test_replace_once_rejects_template_drift(self):
        with self.assertRaises(SystemExit):
            init_project._replace_once("missing placeholder", "expected", "replacement")


if __name__ == "__main__":
    unittest.main()
