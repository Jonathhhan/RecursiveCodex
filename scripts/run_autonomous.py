from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from _mini_yaml import load
from generative_kernel import append_event, read_journal, replay, select_next
from validate_change_event import validate as validate_event
from validate_project import validate

SYSTEM_AUTHORITY = "recursive-codex-system"
QUIESCENCE_SENTINEL = "RECURSIVE_CODEX_QUIESCENT"


def is_autonomous_contract(contract: dict) -> bool:
    authority = contract.get("authority")
    return isinstance(authority, dict) and authority.get("final_decision") == SYSTEM_AUTHORITY


def resolve_command_prefix(executable: str) -> list[str]:
    return [shutil.which(executable) or executable]


def build_command(
    executable: str, root: Path, output: Path, prompt: str, schema: Path
) -> list[str]:
    return [
        *resolve_command_prefix(executable),
        "-a",
        "never",
        "exec",
        "--skip-git-repo-check",
        "-C",
        str(root),
        "-s",
        "read-only",
        "--output-schema",
        str(schema),
        "-o",
        str(output),
        "-",
    ]


def strategic_context(journal: Path) -> dict | None:
    events = read_journal(journal)
    if not events:
        return None
    return select_next(replay(events))


def strategic_instruction(selection: dict | None) -> str:
    if not selection or selection.get("status") != "selected":
        return ""
    goal = selection["goal"]
    context = {
        "goal": goal,
        "failed_strategies": selection.get("failed_strategies", []),
    }
    return (
        "\nThe generative kernel selected this authoritative strategic context for "
        f"candidate prioritization:\n{json.dumps(context, ensure_ascii=False, sort_keys=True)}\n"
    )


def autonomous_prompt(plugin_root: Path, selection: dict | None = None) -> str:
    skill_path = plugin_root / "skills" / "recursive-codex" / "SKILL.md"
    workflow = skill_path.read_text(encoding="utf-8")
    project_validator = plugin_root / "scripts" / "validate_project.py"
    event_validator = plugin_root / "scripts" / "validate_change_event.py"
    return f"""Apply the embedded Recursive Codex workflow in fully autonomous mode for exactly one operation.
The embedded workflow is authoritative for this invocation even if $recursive-codex is not separately installed.
Read the project contract, local domain profile, stabilized events, decisions, current repository state, and checks.
Derive the highest-priority admissible operation from failed checks, contradictions, relational consequences, or deferred possibilities.
Preserve protected paths, provenance, recovery, validation, sandbox, and resource invariants.
If an admissible operation exists, prepare one unified Git patch containing a new change event with status proposed and validation: [], a new accepted system decision, implementation, and tests. Do not run write-requiring checks and do not modify project files directly; the parent owns checks, evidence, and stabilization.
Use these validators in addition to domain checks:
- python {project_validator} <project-root>
- python {event_validator} <event-file>
{strategic_instruction(selection)}
Return only the JSON required by the output schema. Use status quiescent with an empty patch when no operation is admissible. Use status proposal with the complete unified patch otherwise.
Do not start more than one operation in this invocation.

<recursive_codex_workflow>
{workflow}
</recursive_codex_workflow>"""


_GIT_ESCAPE_BYTES = {
    "a": 7,
    "b": 8,
    "f": 12,
    "n": 10,
    "r": 13,
    "t": 9,
    "v": 11,
    "\\": 92,
    '"': 34,
}


def decode_git_path_token(token: str) -> str | None:
    if not token.startswith('"'):
        return token if '"' not in token else None
    if len(token) < 2 or not token.endswith('"'):
        return None
    content = token[1:-1]
    decoded = bytearray()
    index = 0
    while index < len(content):
        character = content[index]
        if character != "\\":
            decoded.extend(character.encode("utf-8"))
            index += 1
            continue
        index += 1
        if index >= len(content):
            return None
        escape = content[index]
        if escape in _GIT_ESCAPE_BYTES:
            decoded.append(_GIT_ESCAPE_BYTES[escape])
            index += 1
            continue
        if escape not in "01234567":
            return None
        end = index
        while end < len(content) and end < index + 3 and content[end] in "01234567":
            end += 1
        value = int(content[index:end], 8)
        if value > 255:
            return None
        decoded.append(value)
        index = end
    try:
        return decoded.decode("utf-8")
    except UnicodeDecodeError:
        return None


def parse_diff_header(header: str) -> tuple[str, str] | None:
    tokens = re.findall(r'"(?:[^"\\]|\\.)*"|\S+', header)
    if len(tokens) != 2 or " ".join(tokens) != header:
        return None
    source = decode_git_path_token(tokens[0])
    target = decode_git_path_token(tokens[1])
    if source is None or target is None or not source.startswith("a/") or not target.startswith("b/"):
        return None
    return source[2:], target[2:]


def parse_file_header(header: str, prefix: str) -> str | None:
    if header == "/dev/null":
        return header
    if not header.startswith('"') and any(character.isspace() for character in header):
        return None
    decoded = decode_git_path_token(header)
    if decoded is None or not decoded.startswith(prefix):
        return None
    return decoded[2:]


def patch_paths(patch: str) -> set[str]:
    paths: set[str] = set()
    for marker, header in re.findall(r"^(---|\+\+\+) (.+)$", patch, re.MULTILINE):
        value = parse_file_header(header, "a/" if marker == "---" else "b/")
        if value is not None and value != "/dev/null":
            paths.add(value)
    for header in re.findall(r"^diff --git (.+)$", patch, re.MULTILINE):
        parsed = parse_diff_header(header)
        if parsed is not None:
            paths.update(parsed)
    return paths


def unsupported_patch_headers(patch: str) -> bool:
    file_headers = any(
        parse_file_header(header, "a/" if marker == "---" else "b/") is None
        for marker, header in re.findall(r"^(---|\+\+\+) (.+)$", patch, re.MULTILINE)
    )
    return any(
        parse_diff_header(header) is None
        for header in re.findall(r"^diff --git (.+)$", patch, re.MULTILINE)
    ) or file_headers


def proposal_authority_errors(
    event_data: object, decision_data: object, decision_path: str
) -> list[str]:
    errors: list[str] = []
    if not isinstance(decision_data, dict):
        errors.append("proposal system decision must be a mapping")
    else:
        if decision_data.get("status") != "accepted":
            errors.append("proposal system decision must be accepted")
        if decision_data.get("authority") != SYSTEM_AUTHORITY:
            errors.append(f"proposal decision authority must be {SYSTEM_AUTHORITY}")
        statement = decision_data.get("decision")
        if not isinstance(statement, str) or not statement.strip():
            errors.append("proposal system decision must contain a decision statement")

    if not isinstance(event_data, dict):
        errors.append("proposal change event must be a mapping")
    else:
        authority = event_data.get("authority")
        if not isinstance(authority, dict):
            errors.append("proposal event authority must be a mapping")
        else:
            if authority.get("status") != "accepted":
                errors.append("proposal event authority must be accepted")
            if authority.get("reference") != decision_path:
                errors.append("proposal event must reference its new system decision")
    return errors


def apply_proposal(
    root: Path,
    runtime: Path,
    patch: str,
    protected: list[str],
    checks: list[str],
    timeout: float,
) -> list[str]:
    paths = patch_paths(patch)
    errors: list[str] = []
    if unsupported_patch_headers(patch):
        errors.append("proposal patch contains an unsupported or ambiguous path header")
    event_paths = sorted(path for path in paths if path.startswith(".recursive-codex/events/"))
    decision_paths = sorted(path for path in paths if path.startswith(".recursive-codex/decisions/"))
    if not paths:
        errors.append("proposal patch has no paths")
    if len(event_paths) != 1:
        errors.append("proposal patch must include exactly one change event")
    if len(decision_paths) != 1:
        errors.append("proposal patch must include exactly one system decision")
    protected_paths = {Path(item).as_posix() for item in protected}
    protected_paths.add(".recursive-codex/project.yaml")
    for value in paths:
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts or value.startswith(".git/"):
            errors.append(f"unsafe proposal path: {value}")
        if any(value == item or value.startswith(f"{item}/") for item in protected_paths):
            errors.append(f"protected proposal path: {value}")
    if event_paths and (root / event_paths[0]).exists():
        errors.append("proposal change event must be new")
    if decision_paths and (root / decision_paths[0]).exists():
        errors.append("proposal system decision must be new")
    if errors:
        return errors

    runtime.mkdir(parents=True, exist_ok=True)
    patch_file = runtime / "proposal.patch"
    patch_file.write_text(patch, encoding="utf-8")
    check = subprocess.run(["git", "apply", "--recount", "--ignore-space-change", "--check", str(patch_file)], cwd=root, check=False)
    if check.returncode != 0:
        return ["git apply --check rejected proposal"]
    applied = subprocess.run(["git", "apply", "--recount", "--ignore-space-change", str(patch_file)], cwd=root, check=False)
    if applied.returncode != 0:
        return ["git apply rejected proposal"]

    event = root / event_paths[0]
    proposed_text = event.read_text(encoding="utf-8")

    def rollback(messages: list[str]) -> list[str]:
        if event.exists():
            event.write_text(proposed_text, encoding="utf-8")
        subprocess.run(["git", "apply", "--recount", "--ignore-space-change", "-R", str(patch_file)], cwd=root, check=False)
        return messages

    if "status: proposed" not in proposed_text or "validation: []" not in proposed_text:
        return rollback(["proposal event must have status proposed and empty validation"])

    try:
        event_data = load(event)
        decision_data = load(root / decision_paths[0])
    except (OSError, ValueError) as exc:
        return rollback([f"invalid proposal authority record: {exc}"])
    authority_errors = proposal_authority_errors(
        event_data,
        decision_data,
        decision_paths[0],
    )
    if authority_errors:
        return rollback(authority_errors)

    post_errors = validate(root)
    for candidate in (root / ".recursive-codex" / "events").glob("*.yaml"):
        post_errors.extend(f"{candidate.name}: {error}" for error in validate_event(candidate))
    if post_errors:
        return rollback(post_errors)

    for declared_check in checks:
        try:
            completed = subprocess.run(
                declared_check,
                cwd=root,
                shell=True,
                check=False,
                timeout=timeout if timeout > 0 else None,
            )
        except subprocess.TimeoutExpired:
            return rollback([f"declared check timed out: {declared_check}"])
        if completed.returncode != 0:
            return rollback([f"declared check failed: {declared_check}"])

    validation = (
        "validation:\n"
        "  - check: parent controller executed all declared project checks\n"
        "    result: passed\n"
        "  - check: parent controller validated project and all change events\n"
        "    result: passed"
    )
    stabilized_text = proposed_text.replace("validation: []", validation, 1).replace(
        "status: proposed", "status: stabilized", 1
    )
    event.write_text(stabilized_text, encoding="utf-8")
    final_errors = validate(root) + [
        f"{event.name}: {error}" for error in validate_event(event)
    ]
    if final_errors:
        return rollback(final_errors)
    return []

def record_failed_attempt(
    journal: Path, selection: dict | None, strategy: str, reason: str
) -> None:
    if selection and selection.get("status") == "selected":
        append_event(journal, "attempt-recorded", {
            "goal": selection["goal"]["id"], "strategy": strategy,
            "status": "failed", "reason": reason,
        })


def execute_child(
    command: list[str], root: Path, timeout: float, prompt: str = ""
) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            command,
            cwd=root,
            check=False,
            timeout=timeout if timeout > 0 else None,
            input=prompt,
            text=True,
        )
    except subprocess.TimeoutExpired:
        return None


def run(
    root: Path,
    executable: str,
    max_cycles: int,
    interval: float,
    cycle_timeout: float,
    dry_run: bool,
) -> int:
    root = root.resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    contract = load(root / ".recursive-codex" / "project.yaml")
    if not isinstance(contract, dict) or not is_autonomous_contract(contract):
        print(f"ERROR: authority.final_decision must be {SYSTEM_AUTHORITY}", file=sys.stderr)
        return 1

    runtime = root / ".recursive-codex" / "runtime"
    output = runtime / "last-message.txt"
    plugin_root = Path(__file__).resolve().parents[1]
    schema = plugin_root / "schemas" / "autonomous-result.schema.json"
    if dry_run:
        command = build_command(executable, root, output, autonomous_prompt(plugin_root), schema)
        print(subprocess.list2cmdline(command))
        return 0

    runtime.mkdir(parents=True, exist_ok=True)
    journal = runtime / "generative-kernel.jsonl"
    cycle = 0
    while max_cycles == 0 or cycle < max_cycles:
        cycle += 1
        try:
            selection = strategic_context(journal)
        except ValueError as exc:
            print(f"INVARIANT ERROR: invalid generative journal: {exc}", file=sys.stderr)
            return 1
        if selection and selection.get("status") == "blocked":
            print(f"AUTONOMOUS BLOCKED {json.dumps(selection['blocked'], sort_keys=True)}")
            return 0
        if selection and selection.get("status") == "quiescent":
            print("AUTONOMOUS STRATEGIC QUIESCENCE")
            return 0
        prompt = autonomous_prompt(plugin_root, selection)
        command = build_command(
            executable, root, output, prompt, schema
        )
        stamp = datetime.now(timezone.utc).isoformat()
        print(f"AUTONOMOUS CYCLE {cycle} {stamp}", flush=True)
        completed = execute_child(command, root, cycle_timeout, prompt)
        if completed is None:
            record_failed_attempt(journal, selection, "codex child execution", f"timeout after {cycle_timeout} seconds")
            print(f"ERROR: autonomous cycle exceeded {cycle_timeout} seconds", file=sys.stderr)
            return 124
        if completed.returncode != 0:
            record_failed_attempt(journal, selection, "codex child execution", f"codex exec exited with {completed.returncode}")
            print(f"ERROR: codex exec exited with {completed.returncode}", file=sys.stderr)
            return completed.returncode
        message = output.read_text(encoding="utf-8") if output.is_file() else ""
        try:
            result = json.loads(message)
        except json.JSONDecodeError as exc:
            print(f"ERROR: invalid autonomous result: {exc}", file=sys.stderr)
            return 1
        if result.get("status") == "quiescent":
            print("AUTONOMOUS QUIESCENCE")
            return 0
        selected_goal = (
            selection["goal"]["id"]
            if selection and selection.get("status") == "selected"
            else None
        )
        strategy = result.get("summary", "autonomous proposal")
        paths = contract.get("paths") if isinstance(contract.get("paths"), dict) else {}
        protected = paths.get("protected") if isinstance(paths.get("protected"), list) else []
        declared_checks = contract.get("checks") if isinstance(contract.get("checks"), list) else []
        errors = apply_proposal(
            root,
            runtime,
            result.get("patch", ""),
            protected,
            declared_checks,
            cycle_timeout,
        )
        if errors:
            if selected_goal:
                append_event(
                    journal,
                    "attempt-recorded",
                    {
                        "goal": selected_goal,
                        "strategy": strategy,
                        "status": "failed",
                        "reason": "; ".join(errors),
                    },
                )
            for error in errors:
                print(f"PROPOSAL ERROR: {error}", file=sys.stderr)
            return 1
        if selected_goal:
            append_event(
                journal,
                "attempt-recorded",
                {
                    "goal": selected_goal,
                    "strategy": strategy,
                    "status": "succeeded",
                    "reason": "proposal stabilized by the parent controller",
                },
            )
            append_event(
                journal,
                "outcome-recorded",
                {"id": f"cycle-{cycle}", "goal": selected_goal, "effect": strategy},
            )
        print(result.get("summary", "AUTONOMOUS PROPOSAL APPLIED"))
        errors = validate(root)
        if errors:
            for error in errors:
                print(f"INVARIANT ERROR: {error}", file=sys.stderr)
            return 1
        if interval > 0:
            time.sleep(interval)
    print(f"AUTONOMOUS CYCLE LIMIT {max_cycles}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run unattended Recursive Codex operations.")
    parser.add_argument("project_root")
    parser.add_argument("--codex", default="codex")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means no cycle limit")
    parser.add_argument("--interval", type=float, default=0)
    parser.add_argument(
        "--cycle-timeout",
        type=float,
        default=900,
        help="Maximum seconds for one child operation; 0 disables the timeout",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_cycles < 0 or args.interval < 0 or args.cycle_timeout < 0:
        parser.error("cycle and interval values must be non-negative")
    return run(
        Path(args.project_root),
        args.codex,
        args.max_cycles,
        args.interval,
        args.cycle_timeout,
        args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
