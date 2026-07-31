from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
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
                    "allowed_outputs": [],
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
                    "allowed_outputs": ["artifacts"],
                },
                root,
                10,
            )
        self.assertIsNone(error)

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
                with self.assertRaises(FileExistsError):
                    with controller.WorkspaceLock(lock_path):
                        pass
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
