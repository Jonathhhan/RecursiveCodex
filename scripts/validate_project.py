from __future__ import annotations

import re
import sys
from pathlib import Path

from _mini_yaml import load

DOMAIN_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _is_non_empty_string(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


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
        configured = Path(value)
        if configured.is_absolute() or ".." in configured.parts:
            errors.append(f"paths.{key} must stay inside the project")

    protected = paths.get("protected")
    if not isinstance(protected, list) or not all(isinstance(item, str) for item in protected):
        errors.append("paths.protected must be a list of strings")

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
