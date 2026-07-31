from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "run_autonomous_integration", ROOT / "scripts" / "run_autonomous.py"
)
controller = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(controller)


def new_file_patch(path: str, content: str) -> str:
    lines = content.splitlines()
    additions = "\n".join(f"+{line}" for line in lines)
    return (
        f"diff --git a/{path} b/{path}\n"
        "new file mode 100644\n"
        "--- /dev/null\n"
        f"+++ b/{path}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n"
        f"{additions}\n"
    )


class AutonomousIsolationIntegrationTests(unittest.TestCase):
    def test_validated_candidate_is_promoted_only_after_isolated_check(self):
        decision_path = ".recursive-codex/decisions/9999-isolation-test.yaml"
        event_path = ".recursive-codex/events/9999-isolation-test.yaml"
        decision = """id: decision-isolation-test
date: 2026-07-31
status: accepted
authority: recursive-codex-system
decision: Accept the isolated integration test.
"""
        event = f"""schema_version: 1
id: isolation-test
operation: local_update
goal: Exercise isolated promotion.
baseline: git:HEAD
scope:
  allowed:
    - isolation-result.txt
    - {decision_path}
    - {event_path}
  protected: []
provenance:
  sources: []
  decisions:
    - {decision_path}
changes: []
relations: []
possibilities:
  opened: []
  restricted: []
  deferred: []
variants: []
collective_findings: []
authority:
  required: true
  status: accepted
  reference: {decision_path}
validation: []
recovery:
  strategy: Remove the integration-test files.
status: proposed
"""
        patch = "".join(
            (
                new_file_patch(decision_path, decision),
                new_file_patch(event_path, event),
                new_file_patch("isolation-result.txt", "promoted\n"),
            )
        )
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory) / "project"
            controller.copy_project(ROOT, project)
            errors = controller.apply_proposal(
                project,
                project / ".recursive-codex" / "runtime",
                patch,
                ["docs/GENEALOGY.md"],
                [{
                    "id": "read-only-check",
                    "command": [sys.executable, "-c", "print('validated')"],
                    "allowed_outputs": [],
                }],
                30,
                {
                    "event_id": "isolation-test",
                    "decision_id": "decision-isolation-test",
                    "recovery": "Remove the integration-test files.",
                },
            )
            self.assertEqual(errors, [])
            self.assertEqual(
                (project / "isolation-result.txt").read_text(encoding="utf-8"),
                "promoted\n",
            )
            stabilized = (project / event_path).read_text(encoding="utf-8")
            self.assertIn("status: stabilized", stabilized)
            self.assertIn("parent controller executed all declared project checks", stabilized)


if __name__ == "__main__":
    unittest.main()
