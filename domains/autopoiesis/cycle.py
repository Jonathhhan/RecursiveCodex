#!/usr/bin/env python3
"""Bounded scheduler for one autopoietic generation/execution feedback cycle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for location in (HERE, ROOT / "scripts"):
    if str(location) not in sys.path:
        sys.path.insert(0, str(location))

import bridge  # noqa: E402
import kernel  # noqa: E402
from generative_kernel import read_journal, replay as replay_goals, select_next  # noqa: E402


def unobserved_perturbations(state: dict) -> list[str]:
    return sorted(
        identifier for identifier, item in state["perturbations"].items()
        if item["status"] == "unobserved"
    )


def run_cycle(
    autopoietic_journal: Path,
    generative_journal: Path,
    project_root: Path,
    execute: bool = False,
    controller_command: list[str] | None = None,
    runner=subprocess.run,
) -> dict:
    imported = bridge.import_outcomes(autopoietic_journal, generative_journal)
    auto_state = kernel.replay(read_journal(autopoietic_journal))
    pending_observation = unobserved_perturbations(auto_state)
    if pending_observation:
        return {
            "status": "observation-required",
            "perturbations": pending_observation,
            "imported": imported,
        }

    generated = kernel.generate_next(autopoietic_journal)
    exported = bridge.export_goals(autopoietic_journal, generative_journal)
    selection = select_next(replay_goals(read_journal(generative_journal)))
    if selection["status"] != "selected":
        return {
            "status": selection["status"],
            "generated": generated,
            "exported": exported,
            **({"blocked": selection["blocked"]} if selection["status"] == "blocked" else {}),
        }
    if not execute:
        return {
            "status": "execution-ready",
            "goal": selection["goal"],
            "generated": generated,
            "exported": exported,
        }

    command = controller_command or [
        sys.executable,
        str(ROOT / "scripts" / "run_autonomous.py"),
        str(project_root),
        "--max-cycles", "1",
    ]
    completed = runner(
        command, cwd=project_root, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        return {
            "status": "controller-failed",
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    imported = bridge.import_outcomes(autopoietic_journal, generative_journal)
    auto_state = kernel.replay(read_journal(autopoietic_journal))
    pending_observation = unobserved_perturbations(auto_state)
    if pending_observation:
        return {
            "status": "observation-required",
            "perturbations": pending_observation,
            "imported": imported,
        }
    return {"status": "cycle-complete", "imported": imported}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("autopoietic_journal", type=Path)
    parser.add_argument("generative_journal", type=Path)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run_cycle(
        args.autopoietic_journal,
        args.generative_journal,
        args.project_root.resolve(),
        execute=args.execute,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if result["status"] == "controller-failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
