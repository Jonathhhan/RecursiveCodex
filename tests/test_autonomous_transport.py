import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("run_autonomous_transport", ROOT / "scripts" / "run_autonomous.py")
controller = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(controller)


class AutonomousTransportTests(unittest.TestCase):
    def test_command_uses_stdin_sentinel(self):
        command = controller.build_command("codex", Path("project"), Path("out"), "prompt", Path("schema"))
        self.assertEqual(command[-1], "-")
        self.assertNotIn("prompt", command)

    def test_child_receives_prompt_through_stdin(self):
        with mock.patch.object(controller.subprocess, "run") as process:
            controller.execute_child(["codex", "-"], Path("project"), 3, "long prompt")
        process.assert_called_once_with(
            ["codex", "-"], cwd=Path("project"), check=False, timeout=3,
            input="long prompt", text=True,
        )

    def test_child_failure_is_recorded_for_selected_goal(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory) / "journal.jsonl"
            controller.append_event(journal, "goal-added", {
                "id": "goal", "level": "strategic", "priority": 1, "requires": []
            })
            selection = controller.strategic_context(journal)
            controller.record_failed_attempt(journal, selection, "child", "exit code 2")
            state = controller.replay(controller.read_journal(journal))
        self.assertEqual(state["attempts"][-1]["reason"], "exit code 2")


if __name__ == "__main__":
    unittest.main()
