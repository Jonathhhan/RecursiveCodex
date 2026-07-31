#!/usr/bin/env python3
"""Audit a Recursive Codex project, its record graph, journals, and workspace."""

from __future__ import annotations

import argparse
import json
import hashlib
import re
import sys
import subprocess
from pathlib import Path
SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


from _mini_yaml import load
from generative_kernel import read_journal
from validate_change_event import validate as validate_event
from validate_project import validate as validate_project
from trust_policy import bootstrap

STRUCTURED_BASELINE = re.compile(r"^stabilized event (?P<path>\.recursive-codex/events/[^ ]+\.yaml)$")
EXTERNAL_BASELINES = {"empty-repository", "git:HEAD"}


def _records(directory: Path, kind: str, errors: list[str]) -> list[tuple[Path, dict]]:
    records: list[tuple[Path, dict]] = []
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = load(path)
        except (OSError, ValueError) as exc:
            errors.append(f"{kind} {path.name} cannot be loaded: {exc}")
            continue
        if not isinstance(data, dict):
            errors.append(f"{kind} {path.name} must be a mapping")
            continue
        records.append((path, data))
    return records


def _unique_ids(records: list[tuple[Path, dict]], kind: str, errors: list[str]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for path, data in records:
        identifier = data.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            errors.append(f"{kind} {path.name} has no non-empty id")
        elif identifier in result:
            errors.append(f"duplicate {kind} id {identifier}: {result[identifier].name}, {path.name}")
        else:
            result[identifier] = path
    return result


def _cycle_errors(edges: dict[str, str]) -> list[str]:
    errors: list[str] = []
    complete: set[str] = set()
    for start in edges:
        if start in complete:
            continue
        order: list[str] = []
        positions: dict[str, int] = {}
        current = start
        while current in edges and current not in complete:
            if current in positions:
                cycle = order[positions[current]:] + [current]
                errors.append("event baseline cycle: " + " -> ".join(cycle))
                break
            positions[current] = len(order)
            order.append(current)
            current = edges[current]
        complete.update(order)
    return errors


def _promotion_receipt(root: Path, errors: list[str]) -> dict | None:
    path = root / ".recursive-codex" / "runtime" / "last-promotion.json"
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        errors.append(f"promotion receipt cannot be loaded: {exc}")
        return None
    candidate = value.get("candidate_digest") if isinstance(value, dict) else None
    real = value.get("real_digest") if isinstance(value, dict) else None
    equal = value.get("equal") if isinstance(value, dict) else None
    if not all(isinstance(item, str) and len(item) == 64 for item in (candidate, real)) or equal is not True or candidate != real:
        errors.append("promotion receipt does not bind equal candidate and real digests")
    return value


def audit(root: Path) -> dict:
    root = root.resolve()
    errors = list(validate_project(root))
    warnings: list[str] = []
    events_dir = root / ".recursive-codex" / "events"
    decisions_dir = root / ".recursive-codex" / "decisions"
    events = _records(events_dir, "event", errors)
    bootstrap_record = bootstrap()
    promotion = _promotion_receipt(root, errors)
    decisions = _records(decisions_dir, "decision", errors)
    event_ids = _unique_ids(events, "event", errors)
    decision_ids = _unique_ids(decisions, "decision", errors)
    event_paths = {path.relative_to(root).as_posix(): data for path, data in events}
    decision_paths = {path.relative_to(root).as_posix(): data for path, data in decisions}

    for path, _ in events:
        errors.extend(f"event {path.name}: {item}" for item in validate_event(path))

    edges: dict[str, str] = {}
    for path, event in events:
        relative = path.relative_to(root).as_posix()
        authority = event.get("authority")
        reference = authority.get("reference") if isinstance(authority, dict) else None
        if isinstance(reference, str) and reference.startswith(".recursive-codex/decisions/"):
            if reference not in decision_paths:
                errors.append(f"event {path.name} references missing decision: {reference}")
            else:
                backref = decision_paths[reference].get("event")
                if backref is not None and backref != relative:
                    errors.append(f"decision {Path(reference).name} points to {backref}, not {relative}")
        provenance = event.get("provenance")
        references = provenance.get("decisions", []) if isinstance(provenance, dict) else []
        if isinstance(references, list):
            for reference in references:
                if isinstance(reference, str) and reference.startswith(".recursive-codex/decisions/") and reference not in decision_paths:
                    errors.append(f"event {path.name} provenance references missing decision: {reference}")

        baseline = event.get("baseline")
        match = STRUCTURED_BASELINE.fullmatch(baseline) if isinstance(baseline, str) else None
        if match:
            target = match.group("path")
            if target not in event_paths:
                errors.append(f"event {path.name} references missing baseline: {target}")
            else:
                edges[relative] = target
        elif baseline not in EXTERNAL_BASELINES:
            warnings.append(f"event {path.name} uses legacy baseline: {baseline}")

    errors.extend(_cycle_errors(edges))
    for path, decision in decisions:
        event = decision.get("event")
        if event is not None and event not in event_paths:
            errors.append(f"decision {path.name} references missing event: {event}")

    journals: dict[str, int] = {}
    runtime = root / ".recursive-codex" / "runtime"
    for name in ("generative-kernel.jsonl", "autopoiesis.jsonl"):
        path = runtime / name
        if path.exists():
            try:
                journals[name] = len(read_journal(path))
            except ValueError as exc:
                errors.append(f"journal {name}: {exc}")

    completed = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=False,
        capture_output=True, text=True,
    )
    workspace = "unknown"
    if completed.returncode == 0:
        workspace = "clean" if not completed.stdout.strip() else "dirty"
        if workspace == "dirty":
            warnings.append("workspace has uncommitted changes")
    else:
        warnings.append("workspace git status is unavailable")

    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "events": len(events), "event_ids": len(event_ids),
            "decisions": len(decisions), "decision_ids": len(decision_ids),
            "structured_baselines": len(edges), "journals": journals,
        },
        "workspace": workspace,
        "bootstrap": bootstrap_record,
        "last_promotion": promotion,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = audit(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"AUDIT {report['status'].upper()} {args.root.resolve()}")
        print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))
        for warning in report["warnings"]:
            print(f"WARNING: {warning}")
        for error in report["errors"]:
            print(f"ERROR: {error}")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
