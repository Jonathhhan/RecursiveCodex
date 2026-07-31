from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "run_autonomous_security", ROOT / "scripts" / "run_autonomous.py"
)
controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(controller)


class AutonomousSecurityTests(unittest.TestCase):
    def test_structured_check_rejects_forbidden_workspace_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "existing.txt").write_text("stable", encoding="utf-8")
            error = controller.isolated_check_error(
                {
                    "id": "writes-forbidden-file",
                    "command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('forbidden.txt').write_text('x')",
                    ],
                    "ephemeral_outputs": [],
                },
                root,
                10,
            )
        self.assertIn("forbidden workspace changes", error)
        self.assertIn("forbidden.txt", error)

    def test_structured_check_permits_declared_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            error = controller.isolated_check_error(
                {
                    "id": "writes-declared-output",
                    "command": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; Path('artifacts').mkdir(); Path('artifacts/result.txt').write_text('x')",
                    ],
                    "ephemeral_outputs": ["artifacts"],
                },
                root,
                10,
            )
        self.assertIsNone(error)

    def test_declared_check_boundary_uses_candidate_cwd_without_shell(self):
        completed = controller.subprocess.CompletedProcess(
            args=["validator", "--check"], returncode=0, stdout="", stderr=""
        )
        with mock.patch.object(controller.subprocess, "run", return_value=completed) as run:
            error = controller.declared_check_error(
                {"id": "validator", "command": ["validator", "--check"]},
                Path("candidate"), 10,
            )
        self.assertIsNone(error)
        _, kwargs = run.call_args
        self.assertEqual(kwargs["cwd"], Path("candidate"))
        self.assertNotIn("shell", kwargs)
        self.assertEqual(run.call_args.args[0], ["validator", "--check"])

    def test_ephemeral_output_may_not_overlap_trust_anchor(self):
        validator = __import__("validate_project")
        for output in (".recursive-codex/events", ".recursive-codex", "scripts"):
            errors = validator._validate_checks(ROOT, [{
                "id": "malicious-output",
                "command": [sys.executable, "-c", "pass"],
                "ephemeral_outputs": [output],
            }], "checks")
            self.assertTrue(
                any("overlaps protected state" in error for error in errors), output
            )

    def test_reverse_patch_failure_stops_hard(self):
        failed = controller.subprocess.CompletedProcess(
            args=["git", "apply", "-R"], returncode=1, stdout="", stderr="cannot reverse"
        )
        with mock.patch.object(controller.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(controller.RollbackFailure, "stopped hard"):
                controller.reverse_patch_or_raise(
                    Path("project"), Path("proposal.patch"), {}
                )

    def test_workspace_lock_is_exclusive_and_records_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "controller.lock"
            with controller.WorkspaceLock(lock_path):
                payload = json.loads(lock_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["pid"], controller.os.getpid())
                self.assertIn("started_at", payload)
                self.assertIsNotNone(payload["process_identity"])
                with self.assertRaises(FileExistsError):
                    with controller.WorkspaceLock(lock_path):
                        pass
            self.assertFalse(lock_path.exists())

    def test_stale_unlock_rejects_active_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "controller.lock"
            started = datetime.now(timezone.utc) - timedelta(hours=2)
            lock_path.write_text(json.dumps({
                "pid": 42, "started_at": started.isoformat(),
                "process_identity": "identity-42",
            }), encoding="utf-8")
            with mock.patch.object(controller, "process_identity", return_value="identity-42"):
                with self.assertRaisesRegex(ValueError, "still active"):
                    controller.unlock_stale_lock(lock_path, 3600)
            self.assertTrue(lock_path.exists())

    def test_stale_unlock_requires_minimum_age(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "controller.lock"
            started = datetime.now(timezone.utc) - timedelta(seconds=30)
            lock_path.write_text(json.dumps({
                "pid": 42, "started_at": started.isoformat(),
                "process_identity": "identity-42",
            }), encoding="utf-8")
            with mock.patch.object(controller, "process_identity", return_value=None):
                with self.assertRaisesRegex(ValueError, "below required"):
                    controller.unlock_stale_lock(lock_path, 3600)
            self.assertTrue(lock_path.exists())

    def test_explicit_stale_unlock_removes_dead_owner_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock_path = Path(directory) / "controller.lock"
            started = datetime.now(timezone.utc) - timedelta(hours=2)
            lock_path.write_text(json.dumps({
                "pid": 42, "started_at": started.isoformat(),
                "process_identity": "identity-42",
            }), encoding="utf-8")
            with mock.patch.object(controller, "process_identity", return_value=None):
                controller.unlock_stale_lock(lock_path, 3600)
            self.assertFalse(lock_path.exists())

    def test_candidate_copy_excludes_git_and_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            destination = Path(directory) / "candidate"
            (source / ".git").mkdir(parents=True)
            (source / ".git" / "config").write_text("secret", encoding="utf-8")
            runtime = source / ".recursive-codex" / "runtime"
            runtime.mkdir(parents=True)
            (runtime / "proposal.patch").write_text("temporary", encoding="utf-8")
            (source / "kept.txt").write_text("kept", encoding="utf-8")
            controller.copy_project(source, destination)
            self.assertTrue((destination / "kept.txt").is_file())
            self.assertFalse((destination / ".git").exists())
            self.assertFalse((destination / ".recursive-codex" / "runtime").exists())


if __name__ == "__main__":
    unittest.main()
