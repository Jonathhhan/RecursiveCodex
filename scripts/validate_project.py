from __future__ import annotations

import re
import sys
from pathlib import Path

from _mini_yaml import load
from artifact_graph import dependency_errors

DOMAIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _safe_project_path(root: Path, value: str) -> Path | None:
    configured = Path(value)
    if configured.is_absolute() or ".." in configured.parts:
        return None
    resolved = (root / configured).resolve()
    try:
        resolved.relative_to(root)
    except ValueError:
        return None
    return resolved


TRUST_ANCHORS = {
    ".recursive-codex/project.yaml", ".recursive-codex/domain.yaml",
    ".recursive-codex/events", ".recursive-codex/decisions",
    "scripts/run_autonomous.py", "scripts/validate_project.py",
    "scripts/validate_change_event.py", "scripts/generative_kernel.py",
    "scripts/validate_discourse.py", "schemas",
}


def _paths_overlap(left: str, right: str) -> bool:
    left = Path(left).as_posix().rstrip("/")
    right = Path(right).as_posix().rstrip("/")
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _validate_checks(
    root: Path, value: object, name: str, protected: list[str] | None = None
) -> list[str]:
    if not isinstance(value, list):
        return [f"{name} must be a list of structured checks"]
    errors: list[str] = []
    identifiers: set[str] = set()
    for index, check in enumerate(value):
        prefix = f"{name}[{index}]"
        if not isinstance(check, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        unknown = set(check) - {"id", "command", "ephemeral_outputs"}
        if unknown:
            errors.append(f"{prefix} has unsupported fields: {sorted(unknown)}")
        identifier = check.get("id")
        if not isinstance(identifier, str) or not DOMAIN_PATTERN.fullmatch(identifier):
            errors.append(f"{prefix}.id must contain lowercase letters, digits, and hyphens")
        elif identifier in identifiers:
            errors.append(f"{prefix}.id must be unique")
        else:
            identifiers.add(identifier)
        command = check.get("command")
        if not isinstance(command, list) or not command or not all(
            _is_non_empty_string(item) for item in command
        ):
            errors.append(f"{prefix}.command must be a non-empty string list")
        outputs = check.get("ephemeral_outputs", [])
        if not isinstance(outputs, list) or not all(_is_non_empty_string(item) for item in outputs):
            errors.append(f"{prefix}.ephemeral_outputs must be a string list")
        else:
            forbidden = TRUST_ANCHORS | {Path(item).as_posix() for item in (protected or [])}
            for output_index, output in enumerate(outputs):
                if _safe_project_path(root, output) is None:
                    errors.append(f"{prefix}.ephemeral_outputs[{output_index}] must stay inside the project")
                elif any(_paths_overlap(output, anchor) for anchor in forbidden):
                    errors.append(f"{prefix}.ephemeral_outputs[{output_index}] overlaps protected state")
    return errors


def _validate_artifacts(
    root: Path, value: object, domain_profile: object,
    domain_checks: list[dict], project_checks: object,
) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        return ["artifacts must be a list"]
    errors: list[str] = []
    contract = domain_profile.get("artifact_contract") if isinstance(domain_profile, dict) else None
    identifiers: set[str] = set()
    check_ids = {
        item.get("id") for item in domain_checks if isinstance(item.get("id"), str)
    }
    if isinstance(project_checks, list):
        check_ids.update(
            item.get("id") for item in project_checks
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        )
    for index, artifact in enumerate(value):
        prefix = f"artifacts[{index}]"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix} must be a mapping")
            continue
        unknown = set(artifact) - {"id", "path", "depends_on"}
        if unknown:
            errors.append(f"{prefix} has unsupported fields: {sorted(unknown)}")
        identifier = artifact.get("id")
        if not isinstance(identifier, str) or not DOMAIN_PATTERN.fullmatch(identifier):
            errors.append(f"{prefix}.id must contain lowercase letters, digits, and hyphens")
        elif identifier in identifiers:
            errors.append(f"{prefix}.id must be unique")
        else:
            identifiers.add(identifier)
            if f"artifact-{identifier}" in check_ids:
                errors.append(f"{prefix}.id produces a duplicate effective check id")
        path_value = artifact.get("path")
        configured = _safe_project_path(root, path_value) if isinstance(path_value, str) else None
        if not _is_non_empty_string(path_value) or configured is None:
            errors.append(f"{prefix}.path must stay inside the project")
        elif not configured.is_file():
            errors.append(f"{prefix}.path does not exist: {path_value}")
    errors.extend(dependency_errors(value))
    if contract is not None and not isinstance(contract, dict):
        errors.append("domain artifact_contract must be a mapping")
    elif isinstance(contract, dict):
        validator = contract.get("validator")
        kind = contract.get("kind")
        plugin_root = Path(__file__).resolve().parents[1]
        validator_path = _safe_project_path(plugin_root, validator) if isinstance(validator, str) else None
        if validator_path is None or not validator_path.is_file():
            errors.append("domain artifact_contract.validator must name an installed validator")
        if not _is_non_empty_string(kind):
            errors.append("domain artifact_contract.kind must be set")
    elif value:
        errors.append("artifacts require domain artifact_contract")
    return errors


def validate(root: Path) -> list[str]:
    root = root.resolve()
    contract_path = root / ".recursive-codex" / "project.yaml"
    if not contract_path.is_file():
        return [f"missing project contract: {contract_path}"]
    try:
        data = load(contract_path)
    except (OSError, ValueError) as exc:
        return [f"invalid project contract: {exc}"]

    if not isinstance(data, dict):
        return ["project contract must be a mapping"]

    errors: list[str] = []
    for key in ("schema_version", "project", "domain", "authority", "paths", "checks"):
        if key not in data:
            errors.append(f"missing field: {key}")

    if data.get("schema_version") != 3:
        errors.append("schema_version must be 3")
    if not _is_non_empty_string(data.get("project")):
        errors.append("project must be a non-empty string")

    domain = data.get("domain")
    if not isinstance(domain, str) or not DOMAIN_PATTERN.fullmatch(domain):
        errors.append("domain must contain lowercase letters, digits, and hyphens")

    domain_path = root / ".recursive-codex" / "domain.yaml"
    try:
        domain_profile = load(domain_path)
    except (OSError, ValueError) as exc:
        errors.append(f"invalid domain profile: {exc}")
        domain_profile = None

    domain_checks: list[dict] = []
    if domain_profile is not None:
        if not isinstance(domain_profile, dict):
            errors.append("domain profile must be a mapping")
        else:
            if domain_profile.get("schema_version") != 1:
                errors.append("domain profile schema_version must be 1")
            if isinstance(domain, str) and domain_profile.get("id") != domain:
                errors.append("domain profile id must match project domain")
            domain_authority = domain_profile.get("authority")
            if not isinstance(domain_authority, dict) or not _is_non_empty_string(
                domain_authority.get("default")
            ):
                errors.append("domain profile authority.default must be set")
            if isinstance(domain_profile.get("checks"), list):
                domain_checks = [item for item in domain_profile["checks"] if isinstance(item, dict)]

    authority = data.get("authority")
    if not isinstance(authority, dict):
        errors.append("authority must be a mapping")
    elif not _is_non_empty_string(authority.get("final_decision")):
        errors.append("authority.final_decision must be set")

    paths = data.get("paths")
    if not isinstance(paths, dict):
        errors.append("paths must be a mapping")
        paths = {}

    for key in ("events", "decisions"):
        value = paths.get(key)
        if not _is_non_empty_string(value):
            errors.append(f"paths.{key} must be a non-empty string")
            continue
        configured = _safe_project_path(root, value)
        if configured is None:
            errors.append(f"paths.{key} must stay inside the project")
        elif not configured.is_dir():
            errors.append(f"paths.{key} directory does not exist: {value}")

    protected = paths.get("protected")
    if not isinstance(protected, list) or not all(_is_non_empty_string(item) for item in protected):
        errors.append("paths.protected must be a list of non-empty strings")
    else:
        for index, value in enumerate(protected):
            if _safe_project_path(root, value) is None:
                errors.append(f"paths.protected[{index}] must stay inside the project")

    errors.extend(_validate_checks(root, data.get("checks"), "checks", protected if isinstance(protected, list) else []))
    if isinstance(domain_profile, dict):
        errors.extend(_validate_checks(
            root, domain_profile.get("checks"), "domain profile checks",
            protected if isinstance(protected, list) else [],
        ))

    project_checks = data.get("checks")
    errors.extend(_validate_artifacts(
        root, data.get("artifacts"), domain_profile, domain_checks, project_checks,
    ))
    if isinstance(project_checks, list):
        domain_ids = {item.get("id") for item in domain_checks if isinstance(item.get("id"), str)}
        for index, check in enumerate(project_checks):
            if isinstance(check, dict) and check.get("id") in domain_ids:
                errors.append(
                    f"checks[{index}].id duplicates a domain profile check id")
    return errors


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    errors = validate(root)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID PROJECT {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
