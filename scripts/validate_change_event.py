from __future__ import annotations

import sys
from pathlib import Path

from _mini_yaml import load

OPERATIONS = {"local_update", "composition", "revision", "reorganization", "audit"}
STATUSES = {"proposed", "tested", "stabilized"}
DECISIONS = {"pending", "accepted", "delegated", "not_required"}


def validate(path: Path) -> list[str]:
    try:
        data = load(path)
    except (OSError, ValueError) as exc:
        return [f"invalid event: {exc}"]
    errors = []
    required = ("schema_version", "id", "operation", "goal", "baseline", "scope", "provenance", "changes", "relations", "possibilities", "authority", "validation", "recovery", "status")
    for key in required:
        if key not in data:
            errors.append(f"missing field: {key}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if data.get("operation") not in OPERATIONS:
        errors.append(f"operation must be one of {sorted(OPERATIONS)}")
    if data.get("status") not in STATUSES:
        errors.append(f"status must be one of {sorted(STATUSES)}")
    authority = data.get("authority", {})
    decision = authority.get("status") if isinstance(authority, dict) else None
    if decision not in DECISIONS:
        errors.append(f"authority.status must be one of {sorted(DECISIONS)}")
    if authority.get("required") and decision == "not_required":
        errors.append("required authority cannot be not_required")
    if data.get("status") == "stabilized":
        if decision not in {"accepted", "delegated", "not_required"}:
            errors.append("stabilized event requires an accepted, delegated, or not_required decision")
        validations = data.get("validation")
        if not isinstance(validations, list) or not any(isinstance(item, dict) and item.get("result") == "passed" for item in validations):
            errors.append("stabilized event requires at least one passed validation")
        recovery = data.get("recovery")
        if not isinstance(recovery, dict) or not recovery.get("strategy"):
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
