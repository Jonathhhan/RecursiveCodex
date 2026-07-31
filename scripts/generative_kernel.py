#!/usr/bin/env python3
"""Persistent strategic memory and deterministic goal selection for Recursive Codex."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from _mini_yaml import load
from validate_discourse import validate as validate_discourse

LEVELS = {"strategic": 3, "tactical": 2, "operational": 1}
ATTEMPT_STATUSES = {"failed", "succeeded"}
CAPABILITY_STATUSES = {"available", "missing"}
CLAIM_KINDS = {"technical", "normative"}


def read_journal(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid journal line {number}: {exc}") from exc
        if not isinstance(event, dict) or event.get("schema_version") != 1:
            raise ValueError(f"invalid journal event at line {number}")
        events.append(event)
    return events


def append_event(path: Path, kind: str, payload: dict) -> dict:
    event = {
        "schema_version": 1,
        "kind": kind,
        "time": datetime.now(timezone.utc).isoformat(),
        **payload,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as journal:
        journal.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def _validate_normative_goal(event: dict, base_path: Path) -> None:
    reference = event.get("discourse_event")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("normative goal requires a discourse_event reference")
    path = Path(reference)
    if not path.is_absolute():
        path = base_path / path
    errors = validate_discourse(path)
    if errors:
        raise ValueError(f"normative goal discourse gate failed: {'; '.join(errors)}")
    try:
        discourse_event = load(path)
    except (OSError, ValueError) as exc:
        raise ValueError(f"normative goal discourse gate failed: {exc}") from exc
    discourse = discourse_event.get("discourse") if isinstance(discourse_event, dict) else None
    claims = discourse.get("claims") if isinstance(discourse, dict) else None
    if discourse_event.get("status") != "stabilized":
        raise ValueError("normative goal requires a stabilized discourse event")
    revocation = discourse.get("revocation") if isinstance(discourse, dict) else None
    if isinstance(revocation, dict) and revocation.get("status") == "revoked":
        raise ValueError("normative goal discourse event has been revoked")
    if not isinstance(claims, list) or not any(
        isinstance(claim, dict) and claim.get("kind") == "normative" for claim in claims
    ):
        raise ValueError("normative goal discourse event requires a normative claim")


def replay(events: list[dict], base_path: Path | None = None) -> dict:
    base_path = base_path or Path.cwd()
    state = {"goals": {}, "capabilities": {}, "attempts": [], "outcomes": []}
    for event in events:
        kind = event.get("kind")
        if kind == "goal-added":
            goal_id = event.get("id")
            if not isinstance(goal_id, str) or not goal_id or goal_id in state["goals"]:
                raise ValueError(f"invalid or duplicate goal id: {goal_id!r}")
            level = event.get("level")
            if level not in LEVELS:
                raise ValueError(f"invalid goal level: {level!r}")
            priority = event.get("priority")
            if not isinstance(priority, int) or priority < 0:
                raise ValueError("goal priority must be a non-negative integer")
            claim_kind = event.get("claim_kind", "technical")
            if claim_kind not in CLAIM_KINDS:
                raise ValueError(f"invalid goal claim kind: {claim_kind!r}")
            if claim_kind == "normative":
                _validate_normative_goal(event, base_path)
            goal_state = {
                "id": goal_id, "level": level, "priority": priority,
                "requires": event.get("requires", []), "status": "pending",
            }
            if claim_kind == "normative":
                goal_state.update(claim_kind=claim_kind, discourse_event=event["discourse_event"])
            state["goals"][goal_id] = goal_state
        elif kind == "capability-recorded":
            if event.get("status") not in CAPABILITY_STATUSES:
                raise ValueError("invalid capability status")
            state["capabilities"][event["id"]] = event["status"]
        elif kind == "attempt-recorded":
            if event.get("goal") not in state["goals"] or event.get("status") not in ATTEMPT_STATUSES:
                raise ValueError("attempt references an unknown goal or invalid status")
            state["attempts"].append(event)
        elif kind == "outcome-recorded":
            goal = state["goals"].get(event.get("goal"))
            if goal is None:
                raise ValueError("outcome references an unknown goal")
            goal["status"] = "completed"
            state["outcomes"].append(event)
        else:
            raise ValueError(f"unknown journal event kind: {kind!r}")
    return state


def select_next(state: dict) -> dict:
    pending = [goal for goal in state["goals"].values() if goal["status"] == "pending"]
    selectable = [
        goal for goal in pending
        if all(state["capabilities"].get(item) == "available" for item in goal["requires"])
    ]
    if selectable:
        selectable.sort(key=lambda goal: (-goal["priority"], -LEVELS[goal["level"]], goal["id"]))
        goal = selectable[0]
        failures = [
            {"strategy": item.get("strategy"), "reason": item.get("reason")}
            for item in state["attempts"]
            if item.get("goal") == goal["id"] and item.get("status") == "failed"
        ]
        return {"status": "selected", "goal": goal, "failed_strategies": failures}
    if pending:
        blocked = {
            goal["id"]: [item for item in goal["requires"] if state["capabilities"].get(item) != "available"]
            for goal in pending
        }
        return {"status": "blocked", "blocked": blocked}
    return {"status": "quiescent"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    goal = sub.add_parser("add-goal")
    goal.add_argument("id"); goal.add_argument("--level", choices=LEVELS, required=True)
    goal.add_argument("--priority", type=int, default=0); goal.add_argument("--requires", nargs="*", default=[])
    goal.add_argument("--claim-kind", choices=CLAIM_KINDS, default="technical")
    goal.add_argument("--discourse-event")
    capability = sub.add_parser("capability")
    capability.add_argument("id"); capability.add_argument("--status", choices=CAPABILITY_STATUSES, required=True)
    attempt = sub.add_parser("attempt")
    attempt.add_argument("goal"); attempt.add_argument("--strategy", required=True)
    attempt.add_argument("--status", choices=ATTEMPT_STATUSES, required=True); attempt.add_argument("--reason", required=True)
    outcome = sub.add_parser("outcome")
    outcome.add_argument("id"); outcome.add_argument("--goal", required=True); outcome.add_argument("--effect", required=True)
    sub.add_parser("select"); sub.add_parser("status")
    args = parser.parse_args()
    events = read_journal(args.journal)
    if args.command == "add-goal":
        payload = {
            "id": args.id,
            "level": args.level,
            "priority": args.priority,
            "requires": args.requires,
            "claim_kind": args.claim_kind,
        }
        if args.discourse_event:
            payload["discourse_event"] = args.discourse_event
        replay([*events, {"schema_version": 1, "kind": "goal-added", **payload}])
        append_event(args.journal, "goal-added", payload)
    elif args.command == "capability":
        append_event(args.journal, "capability-recorded", {"id": args.id, "status": args.status})
    elif args.command == "attempt":
        append_event(args.journal, "attempt-recorded", {"goal": args.goal, "strategy": args.strategy, "status": args.status, "reason": args.reason})
    elif args.command == "outcome":
        append_event(args.journal, "outcome-recorded", {"id": args.id, "goal": args.goal, "effect": args.effect})
    state = replay(read_journal(args.journal))
    result = select_next(state) if args.command == "select" else state
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
