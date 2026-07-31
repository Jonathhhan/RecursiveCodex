from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location(
    "generative_kernel_integrity", ROOT / "scripts" / "generative_kernel.py"
)
kernel = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(kernel)


class JournalIntegrityTests(unittest.TestCase):
    def append_pair(self, path: Path):
        first = kernel.append_event(
            path, "goal-added",
            {"id": "goal", "level": "strategic", "priority": 1, "requires": []},
        )
        second = kernel.append_event(
            path, "outcome-recorded",
            {"id": "done", "goal": "goal", "effect": "complete"},
        )
        return first, second

    def test_append_creates_sequence_and_hash_chain(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            first, second = self.append_pair(path)
            events = kernel.read_journal(path)
        self.assertEqual([item["sequence"] for item in events], [1, 2])
        self.assertEqual(first["previous_hash"], kernel.GENESIS_HASH)
        self.assertEqual(second["previous_hash"], first["event_hash"])

    def test_modified_event_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            self.append_pair(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            event = json.loads(lines[0]); event["priority"] = 999
            lines[0] = json.dumps(event, sort_keys=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "invalid journal event hash"):
                kernel.read_journal(path)

    def test_removed_or_reordered_event_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            self.append_pair(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text(lines[1] + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "sequence"):
                kernel.read_journal(path)
            path.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "sequence"):
                kernel.read_journal(path)

    def test_backward_time_is_detected_even_with_recomputed_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            self.append_pair(path)
            events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
            events[1]["time"] = "2000-01-01T00:00:00+00:00"
            events[1]["event_hash"] = kernel.event_hash(events[1])
            path.write_text(
                "\n".join(json.dumps(item, sort_keys=True) for item in events) + "\n",
                encoding="utf-8", newline="\n",
            )
            with self.assertRaisesRegex(ValueError, "time moved backwards"):
                kernel.read_journal(path)

    def test_legacy_migration_is_explicit_and_preserves_source_hash(self):
        legacy = {
            "schema_version": 1,
            "kind": "goal-added",
            "time": "2026-01-01T00:00:00+00:00",
            "id": "goal",
            "level": "strategic",
            "priority": 1,
            "requires": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            path.write_text(json.dumps(legacy) + "\n", encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "invalid journal event"):
                kernel.read_journal(path)
            self.assertEqual(kernel.migrate_journal(path), 1)
            events = kernel.read_journal(path)
            state = kernel.replay(events)
        expected = kernel.hashlib.sha256(kernel._canonical_event(legacy)).hexdigest()
        self.assertEqual(events[0]["legacy_event_hash"], expected)
        self.assertEqual(state["goals"]["goal"]["status"], "pending")

    def test_payload_cannot_override_chain_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            with self.assertRaisesRegex(ValueError, "reserved journal fields"):
                kernel.append_event(
                    path,
                    "goal-added",
                    {"id": "goal", "sequence": 50},
                )
            self.assertFalse(path.exists())

    def test_journal_lock_is_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal.jsonl"
            with kernel.JournalLock(path):
                with self.assertRaises(FileExistsError):
                    with kernel.JournalLock(path):
                        pass


if __name__ == "__main__":
    unittest.main()
