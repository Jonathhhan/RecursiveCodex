from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "run_autonomous", ROOT / "scripts" / "run_autonomous.py"
)
run_autonomous = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(run_autonomous)


class AutonomousControllerTests(unittest.TestCase):
    def test_requires_system_authority(self):
        self.assertTrue(
            run_autonomous.is_autonomous_contract(
                {"authority": {"final_decision": "recursive-codex-system"}}
            )
        )
        self.assertFalse(
            run_autonomous.is_autonomous_contract(
                {"authority": {"final_decision": "project-owner"}}
            )
        )

    def test_effective_checks_execute_domain_before_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            profile = root / ".recursive-codex" / "domain.yaml"
            profile.parent.mkdir()
            profile.write_text(
                "schema_version: 1\nid: neutral\nauthority:\n  default: owner\n"
                "checks:\n  - id: domain-check\n    command:\n      - domain-command\n"
                "    ephemeral_outputs: []\n",
                encoding="utf-8",
            )
            checks = run_autonomous.effective_declared_checks(root, {
                "checks": [{
                    "id": "project-check", "command": ["project-command"],
                    "ephemeral_outputs": [],
                }]
            })
        self.assertEqual([item["id"] for item in checks],
                         ["domain-check", "project-check"])

    def test_resolution_uses_native_path_match(self):
        with mock.patch.object(
            run_autonomous.shutil, "which", return_value="C:/npm/codex.CMD"
        ):
            self.assertEqual(
                run_autonomous.resolve_command_prefix("codex"),
                ["C:/npm/codex.CMD"],
            )
    def test_command_keeps_workspace_sandbox(self):
        command = run_autonomous.build_command(
            "codex", Path("project"), Path("result.txt"), "prompt", Path("schema.json")
        )
        self.assertIn("read-only", command)
        self.assertIn("--skip-git-repo-check", command)
        self.assertIn("never", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_patch_paths_reject_protected_target(self):
        patch = "--- a/docs/GENEALOGY.md\n+++ b/docs/GENEALOGY.md\n"
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, ["docs/GENEALOGY.md"], [], 0
            )
        self.assertIn("protected proposal path: docs/GENEALOGY.md", errors)
        process.assert_not_called()

    def test_pure_rename_cannot_hide_protected_target(self):
        patch = (
            "diff --git a/safe.txt b/safe.txt\n"
            "--- a/safe.txt\n"
            "+++ b/safe.txt\n"
            "diff --git a/docs/GENEALOGY.md b/docs/GENEALOGY-renamed.md\n"
            "similarity index 100%\n"
            "rename from docs/GENEALOGY.md\n"
            "rename to docs/GENEALOGY-renamed.md\n"
        )
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, ["docs/GENEALOGY.md"], [], 0
            )
        self.assertIn("protected proposal path: docs/GENEALOGY.md", errors)
        process.assert_not_called()

    def test_git_quoted_header_decodes_spaces_and_octal_bytes(self):
        header = '"a/safe file.txt" "b/d\\157cs/renamed file.txt"'
        self.assertEqual(
            run_autonomous.parse_diff_header(header),
            ("safe file.txt", "docs/renamed file.txt"),
        )
        patch = f"diff --git {header}\n"
        self.assertFalse(run_autonomous.unsupported_patch_headers(patch))
        self.assertEqual(
            run_autonomous.patch_paths(patch),
            {"safe file.txt", "docs/renamed file.txt"},
        )

    def test_git_quoted_header_cannot_conceal_protected_path(self):
        patch = 'diff --git "a/d\\157cs/GENEALOGY.md" "b/safe file.txt"\n'
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, ["docs/GENEALOGY.md"], [], 0
            )
        self.assertIn("protected proposal path: docs/GENEALOGY.md", errors)
        process.assert_not_called()

    def test_git_quoted_file_headers_cannot_conceal_protected_path(self):
        patch = '--- "a/d\\157cs/GENEALOGY.md"\n+++ "b/d\\157cs/GENEALOGY.md"\n'
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, ["docs/GENEALOGY.md"], [], 0
            )
        self.assertIn("protected proposal path: docs/GENEALOGY.md", errors)
        process.assert_not_called()

    def test_malformed_git_quoted_file_header_is_rejected(self):
        patch = '--- "a/bad\\qpath"\n+++ b/safe.txt\n'
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, [], [], 0
            )
        self.assertIn(
            "proposal patch contains an unsupported or ambiguous path header", errors
        )
        process.assert_not_called()

    def test_ambiguous_diff_header_is_rejected_before_application(self):
        patch = (
            'diff --git "a/safe file.txt" "b/safe file.txt"\n'
            "--- a/safe.txt\n"
            "+++ b/safe.txt\n"
        )
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, [], [], 0
            )
        self.assertNotIn(
            "proposal patch contains an unsupported or ambiguous path header", errors
        )
        self.assertIn("proposal patch must include exactly one change event", errors)
        self.assertIn("proposal patch must include exactly one system decision", errors)
        process.assert_not_called()

    def test_malformed_git_quoted_header_is_rejected(self):
        patch = 'diff --git "a/bad\\qpath" b/safe.txt\n'
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, [], [], 0
            )
        self.assertIn(
            "proposal patch contains an unsupported or ambiguous path header", errors
        )
        process.assert_not_called()

    def test_patch_requires_event_and_decision(self):
        patch = "--- a/file.txt\n+++ b/file.txt\n"
        errors = run_autonomous.apply_proposal(
            Path("project"), Path("runtime"), patch, [], [], 0
        )
        self.assertIn("proposal patch must include exactly one change event", errors)
        self.assertIn("proposal patch must include exactly one system decision", errors)

    def test_no_paths_preserves_header_error(self):
        patch = 'diff --git "a/bad\\qpath" b/safe.txt\n'
        with mock.patch.object(run_autonomous.subprocess, "run") as process:
            errors = run_autonomous.apply_proposal(
                Path("project"), Path("runtime"), patch, [], [], 0
            )
        self.assertIn("proposal patch contains an unsupported or ambiguous path header", errors)
        self.assertIn("proposal patch has no paths", errors)
        process.assert_not_called()

    def test_proposal_authority_accepts_bound_system_decision(self):
        decision_path = ".recursive-codex/decisions/0011-example.yaml"
        errors = run_autonomous.proposal_authority_errors(
            {
                "authority": {
                    "status": "accepted",
                    "reference": decision_path,
                }
            },
            {
                "status": "accepted",
                "authority": "recursive-codex-system",
                "decision": "Accept the example operation.",
            },
            decision_path,
        )
        self.assertEqual(errors, [])

    def test_proposal_authority_rejects_non_system_decision(self):
        decision_path = ".recursive-codex/decisions/0011-example.yaml"
        errors = run_autonomous.proposal_authority_errors(
            {"authority": {"status": "accepted", "reference": decision_path}},
            {
                "status": "accepted",
                "authority": "repository-owner",
                "decision": "Accept the example operation.",
            },
            decision_path,
        )
        self.assertIn(
            "proposal decision authority must be recursive-codex-system", errors
        )

    def test_proposal_authority_rejects_unrelated_event_reference(self):
        errors = run_autonomous.proposal_authority_errors(
            {
                "authority": {
                    "status": "accepted",
                    "reference": ".recursive-codex/decisions/0001-other.yaml",
                }
            },
            {
                "status": "accepted",
                "authority": "recursive-codex-system",
                "decision": "Accept the example operation.",
            },
            ".recursive-codex/decisions/0011-example.yaml",
        )
        self.assertIn("proposal event must reference its new system decision", errors)

    def test_timeout_returns_control_to_controller(self):
        with mock.patch.object(
            run_autonomous.subprocess,
            "run",
            side_effect=run_autonomous.subprocess.TimeoutExpired("codex", 1),
        ):
            self.assertIsNone(
                run_autonomous.execute_child(["codex"], Path("project"), 1)
            )

    def test_declared_check_failure_retains_stdout_and_stderr(self):
        completed = run_autonomous.subprocess.CompletedProcess(
            args="python check.py",
            returncode=1,
            stdout="first failing assertion\n",
            stderr="validation traceback\n",
        )
        with mock.patch.object(
            run_autonomous.subprocess, "run", return_value=completed
        ) as process:
            error = run_autonomous.declared_check_error(
                {"id": "check", "command": ["python", "check.py"]}, Path("project"), 3
            )
        self.assertIn("declared check failed: check", error)
        self.assertIn("stdout:\nfirst failing assertion", error)
        self.assertIn("stderr:\nvalidation traceback", error)
        process.assert_called_once_with(
            ["python", "check.py"],
            cwd=Path("project"),
            check=False,
            timeout=3,
            capture_output=True,
            text=True,
        )

    def test_declared_check_timeout_retains_partial_diagnostics(self):
        timeout = run_autonomous.subprocess.TimeoutExpired(
            "python check.py",
            3,
            output=b"partial output",
            stderr=b"timeout detail",
        )
        with mock.patch.object(
            run_autonomous.subprocess, "run", side_effect=timeout
        ):
            error = run_autonomous.declared_check_error(
                {"id": "check", "command": ["python", "check.py"]}, Path("project"), 3
            )
        self.assertIn("declared check timed out: check", error)
        self.assertIn("stdout:\npartial output", error)
        self.assertIn("stderr:\ntimeout detail", error)

    def test_validation_failure_diagnostic_is_bounded(self):
        diagnostic = run_autonomous.validation_failure_diagnostic(
            "early failure\n" + ("x" * 5000),
            "final diagnostic",
            limit=100,
        )
        self.assertIn("diagnostic truncated", diagnostic)
        self.assertLessEqual(len(diagnostic), 160)
        self.assertTrue(diagnostic.endswith("stderr:\nfinal diagnostic"))

    def test_validation_diagnostic_redacts_recognized_credentials(self):
        private_key = (
            "-----BEGIN PRIVATE KEY-----\n"
            "private-material\n"
            "-----END PRIVATE KEY-----"
        )
        with mock.patch.dict(
            run_autonomous.os.environ,
            {"RECURSIVE_CODEX_API_TOKEN": "inherited-sensitive-value"},
            clear=True,
        ):
            diagnostic = run_autonomous.validation_failure_diagnostic(
                "password=hunter2\n"
                "Authorization: Bearer abc.def-123\n"
                "remote=https://alice:secret@example.test/repository\n"
                f"key={private_key}\n"
                "environment=inherited-sensitive-value",
                None,
            )
        for secret in (
            "hunter2",
            "abc.def-123",
            "alice:secret",
            "private-material",
            "inherited-sensitive-value",
        ):
            self.assertNotIn(secret, diagnostic)
        self.assertIn("password=[REDACTED]", diagnostic)
        self.assertIn("Bearer [REDACTED]", diagnostic)
        self.assertIn("https://[REDACTED]@example.test/repository", diagnostic)
        self.assertIn("[REDACTED PRIVATE KEY]", diagnostic)
        self.assertIn("environment=[REDACTED ENV]", diagnostic)

    def test_validation_diagnostic_redacts_before_truncation(self):
        secret = "sensitive-value-that-must-not-survive"
        with mock.patch.dict(
            run_autonomous.os.environ,
            {"SERVICE_SECRET": secret},
            clear=True,
        ):
            diagnostic = run_autonomous.validation_failure_diagnostic(
                None,
                "context " + ("x" * 200) + secret,
                limit=80,
            )
        self.assertNotIn(secret, diagnostic)
        self.assertIn("[REDACTED ENV]", diagnostic)
        self.assertIn("diagnostic truncated", diagnostic)

    def test_prompt_limits_each_invocation_to_one_operation(self):
        prompt = run_autonomous.autonomous_prompt(ROOT)
        self.assertIn("exactly one operation", prompt)
        self.assertIn("status quiescent", prompt)
        self.assertIn("<recursive_codex_workflow>", prompt)
        self.assertIn("## Run autonomous reproduction", prompt)
        self.assertIn("validate_change_event.py", prompt)

    def test_strategic_context_selects_persistent_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "journal.jsonl"
            run_autonomous.append_event(
                journal,
                "goal-added",
                {"id": "integrate", "level": "strategic", "priority": 10, "requires": []},
            )
            selection = run_autonomous.strategic_context(journal)
        self.assertEqual(selection["status"], "selected")
        self.assertEqual(selection["goal"]["id"], "integrate")

    def test_prompt_includes_selected_goal_and_failed_strategies(self):
        selection = {
            "status": "selected",
            "goal": {
                "id": "integrate",
                "level": "strategic",
                "priority": 10,
                "requires": [],
                "status": "pending",
            },
            "failed_strategies": [
                {"strategy": "mutable state", "reason": "lost provenance"}
            ],
        }
        prompt = run_autonomous.autonomous_prompt(ROOT, selection)
        self.assertIn('"id": "integrate"', prompt)
        self.assertIn('"strategy": "mutable state"', prompt)

    def test_empty_journal_preserves_existing_candidate_derivation(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "missing.jsonl"
            self.assertIsNone(run_autonomous.strategic_context(journal))


if __name__ == "__main__":
    unittest.main()
