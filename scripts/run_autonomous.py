from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from _mini_yaml import load
from artifact_graph import ordered_artifacts
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


def autonomous_prompt(
    plugin_root: Path, selection: dict | None = None, attestation: dict | None = None
) -> str:
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
For a proposal, copy the exact parent attestation values below into the corresponding structured result fields. Derive expected_paths from the complete patch in sorted order; declare risk, recovery, decision_id, and event_id consistently with the patch. Critical risk cannot be autonomously accepted.
Parent attestation context:
{json.dumps(attestation or {}, ensure_ascii=False, sort_keys=True)}
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


_SENSITIVE_ENVIRONMENT_NAME = re.compile(
    r"(?:^|_)(?:API_?KEY|AUTH|CREDENTIAL|PASS(?:WORD|WD)?|PRIVATE_?KEY|SECRET|TOKEN)(?:_|$)",
    re.IGNORECASE,
)
_PRIVATE_KEY_BLOCK = re.compile(
    r"-----BEGIN (?P<kind>[^\r\n-]*PRIVATE KEY)-----.*?"
    r"-----END (?P=kind)-----",
    re.DOTALL,
)
_CREDENTIAL_URL = re.compile(
    r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)[^\s/:@]+:[^\s/@]+@",
    re.IGNORECASE,
)
_BEARER_TOKEN = re.compile(
    r"\bBearer\s+[A-Za-z0-9._~+/=-]+",
    re.IGNORECASE,
)
_LABELED_CREDENTIAL = re.compile(
    r"(?P<label>\b(?:access[_-]?key|api[_-]?key|client[_-]?secret|credential|"
    r"password|passwd|private[_-]?key|secret|token)\b\s*[:=]\s*)"
    r"(?:\"[^\"\r\n]*\"|'[^'\r\n]*'|[^\s,;]+)",
    re.IGNORECASE,
)


def redact_sensitive_diagnostic(
    value: str, environment: dict[str, str] | None = None
) -> str:
    inherited = os.environ if environment is None else environment
    secrets = {
        item
        for name, item in inherited.items()
        if _SENSITIVE_ENVIRONMENT_NAME.search(name)
        and isinstance(item, str)
        and len(item) >= 4
    }
    for secret in sorted(secrets, key=len, reverse=True):
        value = value.replace(secret, "[REDACTED ENV]")
    value = _PRIVATE_KEY_BLOCK.sub("[REDACTED PRIVATE KEY]", value)
    value = _CREDENTIAL_URL.sub(r"\g<scheme>[REDACTED]@", value)
    value = _BEARER_TOKEN.sub("Bearer [REDACTED]", value)
    return _LABELED_CREDENTIAL.sub(r"\g<label>[REDACTED]", value)


def validation_failure_diagnostic(
    stdout: str | bytes | None,
    stderr: str | bytes | None,
    limit: int = 4000,
) -> str:
    sections: list[str] = []
    for label, value in (("stdout", stdout), ("stderr", stderr)):
        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")
        if isinstance(value, str) and value.strip():
            sections.append(
                f"{label}:\n{redact_sensitive_diagnostic(value.strip())}"
            )
    diagnostic = "\n".join(sections)
    if len(diagnostic) <= limit:
        return diagnostic
    return f"[diagnostic truncated to last {limit} characters]\n{diagnostic[-limit:]}"


class RollbackFailure(RuntimeError):
    pass


def _excluded_snapshot_path(relative: Path, ephemeral_outputs: list[str]) -> bool:
    parts = relative.parts
    if not parts:
        return False
    if parts[0] == ".git" or "__pycache__" in parts or relative.suffix == ".pyc":
        return True
    if len(parts) >= 2 and parts[0] == ".recursive-codex" and parts[1] == "runtime":
        return True
    value = relative.as_posix()
    return any(value == item or value.startswith(f"{item}/") for item in ephemeral_outputs)


def snapshot_tree(root: Path, ephemeral_outputs: list[str] | None = None) -> dict[str, str]:
    ephemeral_outputs = [Path(item).as_posix() for item in (ephemeral_outputs or [])]
    snapshot: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if _excluded_snapshot_path(relative, ephemeral_outputs):
            continue
        if path.is_symlink():
            snapshot[relative.as_posix()] = f"symlink:{os.readlink(path)}"
        elif path.is_file():
            snapshot[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return snapshot


def workspace_digest(root: Path) -> str:
    encoded = json.dumps(snapshot_tree(root), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def baseline_commit(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=False,
        capture_output=True, text=True,
    )
    if completed.returncode != 0 or not re.fullmatch(r"[0-9a-f]{40}", completed.stdout.strip()):
        raise ValueError("cannot resolve baseline commit")
    return completed.stdout.strip()


_RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
_CRITICAL_PATHS = {
    ".recursive-codex/project.yaml", ".recursive-codex/domain.yaml",
    "scripts/run_autonomous.py", "scripts/generative_kernel.py",
}


def minimum_proposal_risk(paths: list[str], patch: str) -> str:
    normalized = {Path(path).as_posix() for path in paths}
    if normalized & _CRITICAL_PATHS:
        return "critical"
    high = (
        len(normalized) >= 10
        or "+++ /dev/null" in patch
        or "rename from " in patch
        or any(
            path.startswith(".github/")
            or path.startswith("scripts/validate")
            or path.startswith("schemas/")
            or path == "docs/AUTONOMOUS_SECURITY.md"
            for path in normalized
        )
    )
    return "high" if high else "low"


def proposal_attestation_errors(
    result: dict,
    selected_goal: str | None,
    checks: list[dict],
    expected_commit: str,
    expected_digest: str,
) -> list[str]:
    errors: list[str] = []
    paths = sorted(patch_paths(result.get("patch", "")))
    if result.get("selected_goal") != selected_goal:
        errors.append("proposal selected_goal does not match parent selection")
    if result.get("expected_paths") != paths:
        errors.append("proposal expected_paths do not match patch paths")
    check_ids = [check["id"] for check in checks]
    if result.get("expected_checks") != check_ids:
        errors.append("proposal expected_checks do not match project contract")
    if result.get("baseline_commit") != expected_commit:
        errors.append("proposal baseline_commit does not match parent baseline")
    if result.get("workspace_digest") != expected_digest:
        errors.append("proposal workspace_digest does not match parent baseline")
    declared_risk = result.get("risk")
    minimum_risk = minimum_proposal_risk(paths, result.get("patch", ""))
    if declared_risk not in _RISK_ORDER:
        errors.append("proposal risk is invalid")
    elif _RISK_ORDER[declared_risk] < _RISK_ORDER[minimum_risk]:
        errors.append(f"proposal risk must be at least {minimum_risk}")
    if minimum_risk == "critical" or declared_risk == "critical":
        errors.append("critical proposals require external authority")
    for field in ("recovery", "decision_id", "event_id"):
        if not isinstance(result.get(field), str) or not result[field].strip():
            errors.append(f"proposal {field} must be a non-empty string")
    return errors


def record_attestation_errors(event_data: dict, decision_data: dict, result: dict) -> list[str]:
    errors: list[str] = []
    if event_data.get("id") != result.get("event_id"):
        errors.append("proposal event_id does not match change event")
    if decision_data.get("id") != result.get("decision_id"):
        errors.append("proposal decision_id does not match system decision")
    recovery = event_data.get("recovery")
    strategy = recovery.get("strategy") if isinstance(recovery, dict) else None
    if strategy != result.get("recovery"):
        errors.append("proposal recovery does not match change event")
    return errors


def snapshot_changes(before: dict[str, str], after: dict[str, str]) -> list[str]:
    return sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))


def copy_project(root: Path, destination: Path) -> None:
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if _excluded_snapshot_path(relative, []):
            continue
        if path.is_symlink():
            raise ValueError(f"project copy refuses symbolic link: {relative.as_posix()}")
    shutil.copytree(
        root,
        destination,
        ignore=shutil.ignore_patterns(".git", "runtime", "__pycache__", "*.pyc"),
    )


def declared_check_error(
    declared_check: dict, root: Path, timeout: float,
    placeholders: dict[str, str] | None = None,
) -> str | None:
    identifier = declared_check["id"]
    replacements = placeholders or {}
    command: list[str] = []
    for argument in declared_check["command"]:
        if argument in replacements:
            command.append(replacements[argument])
        elif re.fullmatch(r"<[^<>]+>", argument):
            return f"declared check has unresolved placeholder: {identifier}: {argument}"
        else:
            command.append(argument)
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            check=False,
            timeout=timeout if timeout > 0 else None,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as exc:
        diagnostic = validation_failure_diagnostic(exc.stdout, exc.stderr)
        suffix = f"\n{diagnostic}" if diagnostic else ""
        return f"declared check timed out: {identifier}{suffix}"
    if completed.returncode == 0:
        return None
    diagnostic = validation_failure_diagnostic(completed.stdout, completed.stderr)
    suffix = f"\n{diagnostic}" if diagnostic else ""
    return f"declared check failed: {identifier}{suffix}"


def isolated_check_error(
    declared_check: dict, root: Path, timeout: float,
    placeholders: dict[str, str] | None = None,
) -> str | None:
    ephemeral_outputs = declared_check.get("ephemeral_outputs", [])
    before = snapshot_tree(root, ephemeral_outputs)
    check_error = declared_check_error(declared_check, root, timeout, placeholders)
    after = snapshot_tree(root, ephemeral_outputs)
    changes = snapshot_changes(before, after)
    if changes:
        detail = ", ".join(changes[:20])
        if len(changes) > 20:
            detail += f", ... ({len(changes)} paths total)"
        return f"declared check produced forbidden workspace changes: {declared_check['id']}: {detail}"
    return check_error


def reverse_patch_or_raise(root: Path, patch_file: Path, baseline: dict[str, str]) -> None:
    reversed_patch = subprocess.run(
        ["git", "apply", "--recount", "--ignore-space-change", "-R", str(patch_file)],
        cwd=root, check=False, capture_output=True, text=True,
    )
    if reversed_patch.returncode != 0:
        diagnostic = validation_failure_diagnostic(reversed_patch.stdout, reversed_patch.stderr)
        raise RollbackFailure(f"reverse patch failed; controller stopped hard\n{diagnostic}")
    residue = snapshot_changes(baseline, snapshot_tree(root))
    if residue:
        raise RollbackFailure(
            "rollback left workspace residue; controller stopped hard: " + ", ".join(residue[:20])
        )


def _evaluate_proposal_in_place(
    root: Path,
    runtime: Path,
    patch: str,
    protected: list[str],
    checks: list[dict],
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
    patch_file.write_text(patch, encoding="utf-8", newline="\n")
    check = subprocess.run(["git", "apply", "--recount", "--ignore-space-change", "--check", str(patch_file)], cwd=root, check=False)
    if check.returncode != 0:
        return ["git apply --check rejected proposal"]
    applied = subprocess.run(["git", "apply", "--recount", "--ignore-space-change", str(patch_file)], cwd=root, check=False)
    if applied.returncode != 0:
        return ["git apply rejected proposal"]

    event = root / event_paths[0]
    proposed_text = event.read_text(encoding="utf-8")

    def rollback(messages: list[str]) -> list[str]:
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
        check_error = declared_check_error(
            declared_check, root, timeout, {"<event-file>": event_paths[0]})
        if check_error is not None:
            return rollback([check_error])

    validation = (
        "validation:\n"
        "  - check: parent controller executed all effective domain and project checks\n"
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


def apply_proposal(
    root: Path,
    runtime: Path,
    patch: str,
    protected: list[str],
    checks: list[dict],
    timeout: float,
    attestation: dict | None = None,
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
        candidate_path = Path(value)
        if candidate_path.is_absolute() or ".." in candidate_path.parts or value.startswith(".git/"):
            errors.append(f"unsafe proposal path: {value}")
        if any(value == item or value.startswith(f"{item}/") for item in protected_paths):
            errors.append(f"protected proposal path: {value}")
    if len(event_paths) == 1 and (root / event_paths[0]).exists():
        errors.append("proposal change event must be new")
    if len(decision_paths) == 1 and (root / decision_paths[0]).exists():
        errors.append("proposal system decision must be new")
    if errors:
        return errors

    root = root.resolve()
    baseline = snapshot_tree(root)

    with tempfile.TemporaryDirectory(prefix="recursive-codex-candidate-") as directory:
        candidate = Path(directory) / "project"
        try:
            copy_project(root, candidate)
        except (OSError, ValueError) as exc:
            return [f"candidate isolation failed: {exc}"]
        candidate_runtime = candidate / ".recursive-codex" / "runtime"
        candidate_errors = _evaluate_proposal_in_place(
            candidate, candidate_runtime, patch, protected, [], timeout
        )
        if candidate_errors:
            return candidate_errors
        if len(event_paths) != 1:
            return ["proposal patch must include exactly one change event"]

        if attestation is not None:
            try:
                event_data = load(candidate / event_paths[0])
                decision_data = load(candidate / decision_paths[0])
            except (OSError, ValueError) as exc:
                return [f"invalid attested proposal records: {exc}"]
            attestation_errors = record_attestation_errors(event_data, decision_data, attestation)
            if attestation_errors:
                return attestation_errors

        stabilized_event = (candidate / event_paths[0]).read_bytes()
        stabilized_decision = (candidate / decision_paths[0]).read_bytes()
        for declared_check in checks:
            check_error = isolated_check_error(
                declared_check, candidate, timeout, {"<event-file>": event_paths[0]})
            if check_error is not None:
                return [check_error]
            check_id = declared_check["id"]
            if (candidate / event_paths[0]).read_bytes() != stabilized_event:
                return [f"proposal event changed during declared check: {check_id}"]
            if (candidate / decision_paths[0]).read_bytes() != stabilized_decision:
                return [f"proposal decision changed during declared check: {check_id}"]

        concurrent_changes = snapshot_changes(baseline, snapshot_tree(root))
        if concurrent_changes:
            detail = ", ".join(concurrent_changes[:20])
            return [f"real workspace changed during isolated validation: {detail}"]

        stabilized_text = stabilized_event.decode("utf-8")

    runtime.mkdir(parents=True, exist_ok=True)
    patch_file = runtime / "proposal.patch"
    patch_file.write_text(patch, encoding="utf-8", newline="\n")
    checked = subprocess.run(
        ["git", "apply", "--recount", "--ignore-space-change", "--check", str(patch_file)],
        cwd=root, check=False, capture_output=True, text=True,
    )
    if checked.returncode != 0:
        return ["real workspace rejected validated proposal"]
    applied = subprocess.run(
        ["git", "apply", "--recount", "--ignore-space-change", str(patch_file)],
        cwd=root, check=False, capture_output=True, text=True,
    )
    if applied.returncode != 0:
        return ["real workspace failed to apply validated proposal"]

    event = root / event_paths[0]
    proposed_text = event.read_text(encoding="utf-8")

    def rollback_real(messages: list[str]) -> list[str]:
        if event.exists():
            event.write_text(proposed_text, encoding="utf-8")
        reverse_patch_or_raise(root, patch_file, baseline)
        return messages

    try:
        event.write_text(stabilized_text, encoding="utf-8")
        final_errors = validate(root) + [
            f"{event.name}: {error}" for error in validate_event(event)
        ]
        if final_errors:
            return rollback_real(final_errors)
    except OSError as exc:
        return rollback_real([f"failed to finalize validated proposal: {exc}"])
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


def process_identity(pid: int) -> str | None:
    if pid <= 0:
        return None
    if os.name == "nt":
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        kernel32.OpenProcess.restype = ctypes.c_void_p
        kernel32.GetProcessTimes.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong),
            ctypes.POINTER(ctypes.c_ulonglong), ctypes.POINTER(ctypes.c_ulonglong),
        ]
        kernel32.GetProcessTimes.restype = ctypes.c_int
        kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            creation = ctypes.c_ulonglong()
            exit_time = ctypes.c_ulonglong()
            kernel = ctypes.c_ulonglong()
            user = ctypes.c_ulonglong()
            if not kernel32.GetProcessTimes(
                handle,
                ctypes.byref(creation), ctypes.byref(exit_time),
                ctypes.byref(kernel), ctypes.byref(user),
            ):
                return None
            return f"windows-filetime:{creation.value}"
        finally:
            kernel32.CloseHandle(handle)
    try:
        stat = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
        closing = stat.rfind(")")
        fields = stat[closing + 2:].split()
        return f"proc-start-ticks:{fields[19]}"
    except (OSError, IndexError):
        return None


class WorkspaceLock:
    def __init__(self, path: Path):
        self.path = path
        self.descriptor: int | None = None

    def __enter__(self) -> "WorkspaceLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        payload = json.dumps({
            "pid": os.getpid(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "process_identity": process_identity(os.getpid()),
        }).encode("utf-8")
        os.write(self.descriptor, payload)
        os.fsync(self.descriptor)
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
            self.descriptor = None
        try:
            self.path.unlink()
        except FileNotFoundError:
            pass


def unlock_stale_lock(path: Path, minimum_age: float, now: datetime | None = None) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        pid = payload["pid"]
        started_at = datetime.fromisoformat(payload["started_at"])
        recorded_identity = payload["process_identity"]
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot verify stale lock: {exc}") from exc
    if not isinstance(pid, int) or not isinstance(recorded_identity, str):
        raise ValueError("cannot verify stale lock owner identity")
    if started_at.tzinfo is None:
        raise ValueError("cannot verify stale lock timestamp")
    current_time = now or datetime.now(timezone.utc)
    age = (current_time - started_at).total_seconds()
    if age < minimum_age:
        raise ValueError(f"lock age {age:.0f}s is below required {minimum_age:.0f}s")
    current_identity = process_identity(pid)
    if current_identity == recorded_identity:
        raise ValueError("lock owner process is still active")
    if current_identity is not None and current_identity != recorded_identity:
        # PID reuse is safe only because the recorded process identity differs.
        pass
    try:
        path.unlink()
    except FileNotFoundError as exc:
        raise ValueError("lock disappeared during stale-lock verification") from exc


def effective_declared_checks(root: Path, contract: dict) -> list[dict]:
    """Return domain, artifact, then project checks in deterministic order."""
    domain_profile = load(root / ".recursive-codex" / "domain.yaml")
    if not isinstance(domain_profile, dict):
        raise ValueError("domain profile must be a mapping")
    domain_checks = domain_profile.get("checks")
    project_checks = contract.get("checks")
    if not isinstance(domain_checks, list) or not isinstance(project_checks, list):
        raise ValueError("domain and project checks must be lists")
    artifacts = contract.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ValueError("artifacts must be a list")
    artifact_checks: list[dict] = []
    if artifacts:
        artifact_contract = domain_profile.get("artifact_contract")
        if not isinstance(artifact_contract, dict):
            raise ValueError("artifacts require domain artifact_contract")
        validator = artifact_contract.get("validator")
        kind = artifact_contract.get("kind")
        if not isinstance(validator, str) or not isinstance(kind, str):
            raise ValueError("domain artifact contract is invalid")
        validator_path = Path(__file__).resolve().parents[1] / validator
        for artifact in ordered_artifacts(artifacts):
            artifact_checks.append({
                "id": f"artifact-{artifact['id']}",
                "command": [sys.executable, str(validator_path), kind, artifact["path"]],
                "ephemeral_outputs": [],
            })
    return [*domain_checks, *artifact_checks, *project_checks]


def _run_locked(
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
    contract_paths = contract.get("paths") if isinstance(contract.get("paths"), dict) else {}
    protected = contract_paths.get("protected") if isinstance(contract_paths.get("protected"), list) else []
    try:
        declared_checks = effective_declared_checks(root, contract)
    except (OSError, ValueError) as exc:
        print(f"ERROR: cannot resolve effective checks: {exc}", file=sys.stderr)
        return 1
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
        selected_goal = (
            selection["goal"]["id"]
            if selection and selection.get("status") == "selected"
            else None
        )
        try:
            expected_commit = baseline_commit(root)
        except ValueError as exc:
            print(f"INVARIANT ERROR: {exc}", file=sys.stderr)
            return 1
        expected_digest = workspace_digest(root)
        context = {"selected_goal": selected_goal, "expected_checks": [item["id"] for item in declared_checks], "baseline_commit": expected_commit, "workspace_digest": expected_digest}
        prompt = autonomous_prompt(plugin_root, selection, context)
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
        errors = proposal_attestation_errors(result, selected_goal, declared_checks, expected_commit, expected_digest)
        if errors:
            for error in errors:
                print(f"PROPOSAL ERROR: {error}", file=sys.stderr)
            return 1
        strategy = result.get("summary", "autonomous proposal")
        errors = apply_proposal(
            root,
            runtime,
            result.get("patch", ""),
            protected,
            declared_checks,
            cycle_timeout,
            result,
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


def run(
    root: Path,
    executable: str,
    max_cycles: int,
    interval: float,
    cycle_timeout: float,
    dry_run: bool,
) -> int:
    root = root.resolve()
    if dry_run:
        return _run_locked(root, executable, max_cycles, interval, cycle_timeout, dry_run)
    lock_path = root / ".recursive-codex" / "runtime" / "controller.lock"
    try:
        with WorkspaceLock(lock_path):
            return _run_locked(root, executable, max_cycles, interval, cycle_timeout, dry_run)
    except FileExistsError:
        detail = ""
        try:
            detail = f": {lock_path.read_text(encoding='utf-8')}"
        except OSError:
            pass
        print(f"ERROR: autonomous controller already holds workspace lock{detail}", file=sys.stderr)
        return 73


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
    parser.add_argument("--unlock-stale", action="store_true")
    parser.add_argument("--stale-after", type=float, default=3600)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.max_cycles < 0 or args.interval < 0 or args.cycle_timeout < 0:
        parser.error("cycle and interval values must be non-negative")
    if args.stale_after < 0:
        parser.error("stale-after must be non-negative")
    if args.unlock_stale:
        lock_path = Path(args.project_root).resolve() / ".recursive-codex" / "runtime" / "controller.lock"
        try:
            unlock_stale_lock(lock_path, args.stale_after)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 73
        print(f"UNLOCKED STALE CONTROLLER LOCK {lock_path}")
        return 0
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
