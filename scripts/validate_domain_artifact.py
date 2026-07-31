#!/usr/bin/env python3
"""Validate auditable sidecar artifacts for art, language, logic, and philosophy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED = {
    "art": {
        "title": str,
        "medium": str,
        "materials": list,
        "intention": str,
        "variants_considered": list,
        "critique": list,
        "selection_reason": str,
        "provenance": list,
        "authority_status": str,
    },
    "language": {
        "text": str,
        "audience": str,
        "register": str,
        "semantic_commitments": list,
        "variants_considered": list,
        "selection_reason": str,
    },
    "logic": {
        "premises": list,
        "conclusion": str,
        "logic": str,
        "derivation": list,
        "countermodel_status": str,
    },
    "philosophy": {
        "thesis": str,
        "concepts": list,
        "reasons": list,
        "objections": list,
        "responses": list,
        "sources": list,
        "authority_status": str,
    },
}


def _non_empty(value: object, expected: type) -> bool:
    if not isinstance(value, expected):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return bool(value)


def validate(data: object, expected_kind: str) -> list[str]:
    if expected_kind not in REQUIRED:
        return [f"unsupported artifact kind: {expected_kind}"]
    if not isinstance(data, dict):
        return ["artifact must be a mapping"]
    errors: list[str] = []
    if data.get("kind") != expected_kind:
        errors.append(f"artifact kind must be {expected_kind}")
    for field, expected_type in REQUIRED[expected_kind].items():
        if not _non_empty(data.get(field), expected_type):
            errors.append(f"{field} must be a non-empty {expected_type.__name__}")
    if expected_kind == "logic" and data.get("countermodel_status") not in {
        "found", "not-found", "not-searched", "not-applicable"
    }:
        errors.append("countermodel_status is invalid")
    if expected_kind == "philosophy" and isinstance(data.get("objections"), list):
        responses = data.get("responses")
        if isinstance(responses, list) and len(responses) < len(data["objections"]):
            errors.append("every philosophical objection requires a response")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=sorted(REQUIRED))
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read artifact: {exc}")
        return 1
    errors = validate(data, args.kind)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID {args.kind.upper()} ARTIFACT {args.artifact}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
