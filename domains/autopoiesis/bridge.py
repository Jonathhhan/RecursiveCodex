#!/usr/bin/env python3
"""Auditable bridge between autopoietic operations and execution goals."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCRIPTS = ROOT / "scripts"
for location in (HERE, SCRIPTS):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

import kernel as autopoiesis  # noqa: E402
from generative_kernel import append_event, read_journal, replay as replay_goals  # noqa: E402


def _goal_operation(events: list[dict], goal_id: str) -> dict:
    matches = [
        event for event in events
        if event.get("kind") == "goal-generated" and event.get("id") == goal_id
    ]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one generating operation for {goal_id}")
    return matches[0]


def export_goals(autopoietic_journal: Path, generative_journal: Path) -> list[str]:
    auto_events = read_journal(autopoietic_journal)
    auto_state = autopoiesis.replay(auto_events)
    generative_events = read_journal(generative_journal)
    exported: list[str] = []
    for goal_id, goal in sorted(auto_state["generated_goals"].items()):
        operation = _goal_operation(auto_events, goal_id)
        operation_hash = operation["event_hash"]
        existing = [
            event for event in generative_events
            if event.get("kind") == "goal-added" and event.get("id") == goal_id
        ]
        if existing:
            if len(existing) != 1 or existing[0].get("origin_operation_hash") != operation_hash:
                raise ValueError(f"generative goal collision: {goal_id}")
            generative_event = existing[0]
        else:
            generative_event = append_event(generative_journal, "goal-added", {
                "id": goal_id,
                "level": goal["level"],
                "priority": goal["priority"],
                "requires": goal["requires"],
                "claim_kind": "technical",
                "origin": goal["origin"],
                "origin_operation_hash": operation_hash,
                "summary": goal["summary"],
            })
            generative_events.append(generative_event)
        receipt = auto_state["exports"].get(goal_id)
        if receipt is None:
            append_event(autopoietic_journal, "goal-exported", {
                "id": f"export-{goal_id}",
                "goal": goal_id,
                "operation_hash": operation_hash,
                "generative_event_hash": generative_event["event_hash"],
            })
            exported.append(goal_id)
        elif (
            receipt["operation_hash"] != operation_hash
            or receipt["generative_event_hash"] != generative_event["event_hash"]
        ):
            raise ValueError(f"export receipt mismatch: {goal_id}")
    replay_goals(read_journal(generative_journal))
    autopoiesis.replay(read_journal(autopoietic_journal))
    return exported


def import_outcomes(autopoietic_journal: Path, generative_journal: Path) -> list[str]:
    auto_events = read_journal(autopoietic_journal)
    auto_state = autopoiesis.replay(auto_events)
    imported_sources = {
        event.get("source") for event in auto_events
        if event.get("kind") == "perturbation-recorded"
    }
    imported: list[str] = []
    for event in read_journal(generative_journal):
        if event.get("kind") != "outcome-recorded":
            continue
        goal_id = event.get("goal")
        if goal_id not in auto_state["exports"]:
            continue
        source = f"controller-outcome:{event['event_hash']}"
        if source in imported_sources:
            continue
        identifier = f"outcome-{event['event_hash'][:16]}"
        append_event(autopoietic_journal, "perturbation-recorded", {
            "id": identifier,
            "source": source,
            "signal": str(event.get("effect", "controller outcome")),
            "exported_goal": goal_id,
        })
        imported.append(identifier)
        imported_sources.add(source)
    autopoiesis.replay(read_journal(autopoietic_journal))
    return imported


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("autopoietic_journal", type=Path)
    parser.add_argument("generative_journal", type=Path)
    parser.add_argument("command", choices=("export", "import", "sync"))
    args = parser.parse_args()
    result = {}
    if args.command in {"export", "sync"}:
        result["exported_goals"] = export_goals(args.autopoietic_journal, args.generative_journal)
    if args.command in {"import", "sync"}:
        result["imported_perturbations"] = import_outcomes(args.autopoietic_journal, args.generative_journal)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
