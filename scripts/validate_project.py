from __future__ import annotations

import sys
from pathlib import Path

from _mini_yaml import load


def validate(root: Path) -> list[str]:
    contract_path = root / ".recursive-codex" / "project.yaml"
    if not contract_path.is_file():
        return [f"missing project contract: {contract_path}"]
    try:
        data = load(contract_path)
    except (OSError, ValueError) as exc:
        return [f"invalid project contract: {exc}"]
    errors = []
    for key in ("schema_version", "project", "domain", "authority", "paths", "checks"):
        if key not in data:
            errors.append(f"missing field: {key}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    authority = data.get("authority", {})
    if not isinstance(authority, dict) or not authority.get("final_decision"):
        errors.append("authority.final_decision must be set")
    paths = data.get("paths", {})
    for key in ("events", "decisions", "protected"):
        if not isinstance(paths, dict) or key not in paths:
            errors.append(f"paths.{key} must be set")
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
