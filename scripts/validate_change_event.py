from __future__ import annotations

import re
import sys
from pathlib import Path

from _mini_yaml import load

OPERATIONS = {"local_update", "composition", "revision", "reorganization", "audit"}
STATUSES = {"proposed", "tested", "stabilized"}
DECISIONS = {"pending", "accepted", "delegated", "not_required"}
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def _require_mapping(data: dict, key: str, errors: list[str]) -> dict:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be a mapping")
        return {}
    return value


def _require_list(data: dict, key: str, errors: list[str]) -> list:
    value = data.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} must be a list")
        return []
    return value


def validate(path: Path) -> list[str]:
    try:
        data = load(path)
    except (OSError, ValueError) as exc:
        return [f"invalid event: {exc}"]

    if not isinstance(data, dict):
        return ["event must be a mapping"]

    errors: list[str] = []
    required = (
        "schema_version",
        "id",
        "operation",
        "goal",
        "baseline",
        "scope",
        "provenance",
        "changes",
        "relations",
        "possibilities",
        "authority",
        "validation",
        "recovery",
        "status",
    )
    for key in required:
        if key not in data:
            errors.append(f"missing field: {key}")

    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")

    event_id = data.get("id")
    if not isinstance(event_id, str) or not ID_PATTERN.fullmatch(event_id):
        errors.append("id must contain lowercase letters, digits, and hyphens")

    for key in ("goal", "baseline"):
        if not isinstance(data.get(key), str) or not data.get(key).strip():
            errors.append(f"{key} must be a non-empty string")

    if data.get("operation") not in OPERATIONS:
        errors.append(f"operation must be one of {sorted(OPERATIONS)}")
    if data.get("status") not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")

    _require_mapping(data, "scope", errors)
    _require_mapping(data, "provenance", errors)
    _require_list(data, "changes", errors)
    _require_list(data, "relations", errors)
    _require_mapping(data, "possibilities", errors)
    authority = _require_mapping(data, "authority", errors)
    validations = _require_list(data, "validation", errors)
    recovery = _require_mapping(data, "recovery", errors)

    decision = authority.get("status")
    if decision not in DECISIONS:
        errors.append(f"authority.status must be one of {sorted(DECISIONS)}")
    if authority.get("required") is not None and not isinstance(authority.get("required"), bool):
        errors.append("authority.required must be a boolean")
    if authority.get("required") and decision == "not_required":
        errors.append("required authority cannot be not_required")

    if data.get("status") == "stabilized":
        if decision not in {"accepted", "delegated", "not_required"}:
            errors.append("stabilized event requires an accepted, delegated, or not_required decision")
        if not any(isinstance(item, dict) and item.get("result") == "passed" for item in validations):
            errors.append("stabilized event requires at least one passed validation")
        if not recovery.get("strategy"):
            errors.append("stabilized event requires recovery.strategy")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_change_event.py <event.yaml>")
        return 2
    path = Path(sys.argv[1])
    errors = validate(path)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID EVENT {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
