from __future__ import annotations

import re
import sys
from pathlib import Path

from _mini_yaml import load

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

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
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
            domain_checks = domain_profile.get("checks")
            if not isinstance(domain_checks, list) or not all(
                _is_non_empty_string(item) for item in domain_checks
            ):
                errors.append("domain profile checks must be a list of non-empty strings")

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

    checks = data.get("checks")
    if not isinstance(checks, list) or not all(_is_non_empty_string(item) for item in checks):
        errors.append("checks must be a list of non-empty strings")

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
