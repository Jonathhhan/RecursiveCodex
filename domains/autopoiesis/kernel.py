#!/usr/bin/env python3
"""Experimental autopoietic operation layer for the autopoiesis domain."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
DOMAIN = Path(__file__).resolve().parent
if str(DOMAIN) not in sys.path:
    sys.path.insert(0, str(DOMAIN))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from generative_kernel import append_event, read_journal  # noqa: E402
import forms  # noqa: E402
import propositions  # noqa: E402


def _text(event: dict, field: str) -> str:
    value = event.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{event.get('kind')} requires non-empty {field}")
    return value.strip()


def replay(events: list[dict]) -> dict:
    state = {
        "possible_states": {},
        "propositions": {},
        "proposition_tests": {},
        "representation_limits": {},
        "silences": {},
        "forms": {},
        "perturbations": {},
        "observations": {},
        "tensions": {},
        "generated_goals": {},
        "exports": {},
        "outcomes": [],
        "deferrals": {},
        "selection_observations": {},
        "expectations": {},
    }
    for event in events:
        kind = event.get("kind")
        identifier = _text(event, "id")
        if kind == "distinction-drawn":
            if identifier in state["forms"]:
                raise ValueError(f"duplicate form: {identifier}")
            state["forms"][identifier] = {
                "id": identifier,
                **forms.distinction(
                    _text(event, "marked"), _text(event, "unmarked"),
                    _text(event, "indicated"),
                ),
            }
        elif kind == "form-reentered":
            source = _text(event, "source")
            if source not in state["forms"]:
                raise ValueError("re-entry references unknown form")
            if identifier in state["forms"]:
                raise ValueError(f"duplicate form: {identifier}")
            state["forms"][identifier] = {
                "id": identifier, **forms.reentry(state["forms"][source], _text(event, "side"))
            }
        elif kind == "perturbation-recorded":
            if identifier in state["perturbations"]:
                raise ValueError(f"duplicate perturbation: {identifier}")
            state["perturbations"][identifier] = {
                "id": identifier,
                "source": _text(event, "source"),
                "signal": _text(event, "signal"),
                "status": "unobserved",
            }
        elif kind == "state-of-affairs-configured":
            if identifier in state["possible_states"]:
                raise ValueError(f"duplicate possible state: {identifier}")
            state["possible_states"][identifier] = {
                "id": identifier,
                **propositions.configure_state(event.get("objects"), event.get("relations", [])),
            }
        elif kind == "proposition-formed":
            possible_state = _text(event, "possible_state")
            if possible_state not in state["possible_states"]:
                raise ValueError("proposition references unknown possible state")
            if identifier in state["propositions"]:
                raise ValueError(f"duplicate proposition: {identifier}")
            state["propositions"][identifier] = {
                "id": identifier,
                "possible_state": possible_state,
                **propositions.form_proposition(
                    state["possible_states"][possible_state],
                    _text(event, "text"), event.get("picture"),
                ),
                "status": "untested",
            }
        elif kind == "proposition-tested":
            proposition = _text(event, "proposition")
            if proposition not in state["propositions"]:
                raise ValueError("test references unknown proposition")
            if identifier in state["proposition_tests"]:
                raise ValueError(f"duplicate proposition test: {identifier}")
            result = propositions.test_result(_text(event, "result"), _text(event, "evidence"))
            state["proposition_tests"][identifier] = {
                "id": identifier, "proposition": proposition, **result,
            }
            state["propositions"][proposition]["status"] = result["result"]
        elif kind == "representation-limit-observed":
            if identifier in state["representation_limits"]:
                raise ValueError(f"duplicate representation limit: {identifier}")
            state["representation_limits"][identifier] = {
                "id": identifier, "subject": _text(event, "subject"),
                "reason": _text(event, "reason"),
            }
        elif kind == "silence-entered":
            limit = _text(event, "limit")
            if limit not in state["representation_limits"]:
                raise ValueError("silence references unknown representation limit")
            if identifier in state["silences"]:
                raise ValueError(f"duplicate silence: {identifier}")
            state["silences"][identifier] = {
                "id": identifier, "limit": limit, "reason": _text(event, "reason"),
            }
        elif kind == "observation-produced":
            if identifier in state["observations"]:
                raise ValueError(f"duplicate observation: {identifier}")
            perturbation = _text(event, "perturbation")
            if perturbation not in state["perturbations"]:
                raise ValueError("observation references unknown perturbation")
            form = _text(event, "form")
            if form not in state["forms"]:
                raise ValueError("observation references unknown form")
            proposition = _text(event, "proposition")
            if proposition not in state["propositions"]:
                raise ValueError("observation references unknown proposition")
            state["observations"][identifier] = {
                "id": identifier,
                "perturbation": perturbation,
                "form": form,
                "indication": state["forms"][form]["indicated"],
                "proposition": proposition,
                "description": _text(event, "description"),
            }
            state["perturbations"][perturbation]["status"] = "observed"
        elif kind == "tension-formed":
            if identifier in state["tensions"]:
                raise ValueError(f"duplicate tension: {identifier}")
            observations = event.get("observations")
            if not isinstance(observations, list) or not observations:
                raise ValueError("tension requires observations")
            if not all(item in state["observations"] for item in observations):
                raise ValueError("tension references unknown observation")
            priority = event.get("priority")
            if not isinstance(priority, int) or priority < 0:
                raise ValueError("tension priority must be a non-negative integer")
            state["tensions"][identifier] = {
                "id": identifier,
                "observations": observations,
                "expectation": _text(event, "expectation"),
                "discrepancy": _text(event, "discrepancy"),
                "priority": priority,
                "level": event.get("level", "tactical"),
                "requires": event.get("requires", []),
                "status": "open",
            }
        elif kind == "goal-generated":
            tension = _text(event, "tension")
            if tension not in state["tensions"]:
                raise ValueError("generated goal references unknown tension")
            expected = derive_goal(state, tension)
            if identifier != expected["id"] or event.get("goal") != expected:
                raise ValueError("generated goal does not match internal derivation")
            if identifier in state["generated_goals"]:
                raise ValueError(f"duplicate generated goal: {identifier}")
            state["generated_goals"][identifier] = expected
            state["tensions"][tension]["status"] = "connected"
        elif kind == "goal-exported":
            goal = _text(event, "goal")
            if goal not in state["generated_goals"]:
                raise ValueError("export references unknown generated goal")
            if goal in state["exports"]:
                raise ValueError(f"duplicate goal export: {goal}")
            operation_hash = _text(event, "operation_hash")
            generative_hash = _text(event, "generative_event_hash")
            state["exports"][goal] = {
                "goal": goal,
                "operation_hash": operation_hash,
                "generative_event_hash": generative_hash,
            }
            state["generated_goals"][goal]["status"] = "exported"
        elif kind == "continuation-deferred":
            tension = _text(event, "tension")
            if tension not in state["tensions"] or state["tensions"][tension]["status"] != "open":
                raise ValueError("deferral requires an open tension")
            state["deferrals"][identifier] = {
                "id": identifier,
                "tension": tension,
                "reason": _text(event, "reason"),
            }
            state["tensions"][tension]["status"] = "deferred"
        elif kind == "selection-observed":
            goal = _text(event, "goal")
            if goal not in state["generated_goals"]:
                raise ValueError("selection observation references unknown goal")
            mode = event.get("mode")
            if mode not in {"reproduction", "variation", "reorganization"}:
                raise ValueError("selection observation has invalid mode")
            form = _text(event, "form")
            if form not in state["forms"]:
                raise ValueError("selection observation references unknown form")
            if identifier in state["selection_observations"]:
                raise ValueError(f"duplicate selection observation: {identifier}")
            state["selection_observations"][identifier] = {
                "id": identifier,
                "goal": goal,
                "mode": mode,
                "form": form,
                "description": _text(event, "description"),
            }
        elif kind == "expectation-condensed":
            observations = event.get("observations")
            if not isinstance(observations, list) or len(observations) < 2:
                raise ValueError("condensed expectation requires at least two observations")
            if not all(item in state["selection_observations"] for item in observations):
                raise ValueError("condensed expectation references unknown observation")
            if len(set(observations)) != len(observations):
                raise ValueError("condensed expectation observations must be unique")
            if identifier in state["expectations"]:
                raise ValueError(f"duplicate expectation: {identifier}")
            state["expectations"][identifier] = {
                "id": identifier,
                "observations": observations,
                "expectation": _text(event, "expectation"),
                "status": "active",
            }
        elif kind == "outcome-integrated":
            goal = _text(event, "goal")
            if goal not in state["generated_goals"]:
                raise ValueError("outcome references unknown generated goal")
            state["generated_goals"][goal]["status"] = "completed"
            state["outcomes"].append({
                "id": identifier, "goal": goal, "effect": _text(event, "effect")
            })
        else:
            raise ValueError(f"unknown autopoietic operation: {kind!r}")
    return state


def derive_goal(state: dict, tension_id: str | None = None) -> dict:
    open_tensions = [
        tension for tension in state["tensions"].values()
        if tension["status"] == "open"
    ]
    if tension_id is not None:
        open_tensions = [item for item in open_tensions if item["id"] == tension_id]
    if not open_tensions:
        return {"status": "quiescent"}
    open_tensions.sort(key=lambda item: (-item["priority"], item["id"]))
    tension = open_tensions[0]
    identity = hashlib.sha256(
        json.dumps(tension, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    return {
        "id": f"connection-{identity}",
        "level": tension["level"],
        "priority": tension["priority"],
        "requires": tension["requires"],
        "claim_kind": "technical",
        "summary": f"Address internally observed discrepancy: {tension['discrepancy']}",
        "origin": {"kind": "autopoietic-tension", "id": tension["id"]},
        "structural_expectations": sorted(state["expectations"]),
        "status": "pending",
    }


def generate_next(journal: Path) -> dict:
    state = replay(read_journal(journal))
    goal = derive_goal(state)
    if goal.get("status") == "quiescent":
        return goal
    append_event(journal, "goal-generated", {
        "id": goal["id"], "tension": goal["origin"]["id"], "goal": goal,
    })
    return goal


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("journal", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    distinguish = sub.add_parser("distinguish")
    distinguish.add_argument("id"); distinguish.add_argument("--marked", required=True)
    distinguish.add_argument("--unmarked", required=True); distinguish.add_argument("--indicated", choices=("marked", "unmarked"), required=True)
    reenter = sub.add_parser("reenter")
    reenter.add_argument("id"); reenter.add_argument("--source", required=True); reenter.add_argument("--side", choices=("marked", "unmarked"), required=True)
    perturb = sub.add_parser("perturb")
    perturb.add_argument("id"); perturb.add_argument("--source", required=True); perturb.add_argument("--signal", required=True)
    observe = sub.add_parser("observe")
    observe.add_argument("id"); observe.add_argument("--perturbation", required=True)
    observe.add_argument("--form", required=True)
    observe.add_argument("--description", required=True)
    tension = sub.add_parser("form-tension")
    tension.add_argument("id"); tension.add_argument("--observations", nargs="+", required=True)
    tension.add_argument("--expectation", required=True); tension.add_argument("--discrepancy", required=True)
    tension.add_argument("--priority", type=int, default=0); tension.add_argument("--level", default="tactical")
    tension.add_argument("--requires", nargs="*", default=[])
    defer = sub.add_parser("defer")
    defer.add_argument("id"); defer.add_argument("--tension", required=True); defer.add_argument("--reason", required=True)
    observe_selection = sub.add_parser("observe-selection")
    observe_selection.add_argument("id"); observe_selection.add_argument("--goal", required=True)
    observe_selection.add_argument("--mode", choices=("reproduction", "variation", "reorganization"), required=True)
    observe_selection.add_argument("--form", required=True); observe_selection.add_argument("--description", required=True)
    condense = sub.add_parser("condense-expectation")
    condense.add_argument("id"); condense.add_argument("--observations", nargs="+", required=True)
    condense.add_argument("--expectation", required=True)
    sub.add_parser("generate"); sub.add_parser("status")
    args = parser.parse_args()
    if args.command == "distinguish":
        append_event(args.journal, "distinction-drawn", {"id": args.id, "marked": args.marked, "unmarked": args.unmarked, "indicated": args.indicated})
    elif args.command == "reenter":
        append_event(args.journal, "form-reentered", {"id": args.id, "source": args.source, "side": args.side})
    elif args.command == "perturb":
        append_event(args.journal, "perturbation-recorded", {"id": args.id, "source": args.source, "signal": args.signal})
    elif args.command == "observe":
        append_event(args.journal, "observation-produced", {"id": args.id, "perturbation": args.perturbation, "form": args.form, "description": args.description})
    elif args.command == "form-tension":
        append_event(args.journal, "tension-formed", {"id": args.id, "observations": args.observations, "expectation": args.expectation, "discrepancy": args.discrepancy, "priority": args.priority, "level": args.level, "requires": args.requires})
    elif args.command == "defer":
        append_event(args.journal, "continuation-deferred", {"id": args.id, "tension": args.tension, "reason": args.reason})
    elif args.command == "observe-selection":
        append_event(args.journal, "selection-observed", {"id": args.id, "goal": args.goal, "mode": args.mode, "form": args.form, "description": args.description})
    elif args.command == "condense-expectation":
        append_event(args.journal, "expectation-condensed", {"id": args.id, "observations": args.observations, "expectation": args.expectation})
    elif args.command == "generate":
        print(json.dumps(generate_next(args.journal), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps(replay(read_journal(args.journal)), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
