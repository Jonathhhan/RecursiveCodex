from __future__ import annotations

import sys
from pathlib import Path

from _mini_yaml import load

CLAIM_KINDS = {"factual", "normative", "expressive", "technical"}
OBJECTION_STATUSES = {"addressed", "deferred", "unresolved"}
CLOSURE_STATUSES = {"accepted", "contested", "deferred"}


def _strings(value: object, name: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
        errors.append(f"discourse.{name} must be a non-empty list of strings")
        return []
    return value


def validate(path: Path) -> list[str]:
    try:
        event = load(path)
    except (OSError, ValueError) as exc:
        return [f"invalid event: {exc}"]
    if not isinstance(event, dict):
        return ["event must be a mapping"]
    discourse = event.get("discourse")
    if not isinstance(discourse, dict):
        return ["discourse must be a mapping"]

    errors: list[str] = []
    affected = _strings(discourse.get("affected_roles"), "affected_roles", errors)
    participants = _strings(discourse.get("participants"), "participants", errors)
    claims = discourse.get("claims")
    objections = discourse.get("objections")
    closure = discourse.get("closure")
    revocation = discourse.get("revocation")
    if not isinstance(claims, list) or not claims:
        errors.append("discourse.claims must be a non-empty list")
        claims = []
    if not isinstance(objections, list):
        errors.append("discourse.objections must be a list")
        objections = []
    if not isinstance(closure, dict) or closure.get("status") not in CLOSURE_STATUSES:
        errors.append(f"discourse.closure.status must be one of {sorted(CLOSURE_STATUSES)}")
        closure = {}
    if revocation is not None:
        if not isinstance(revocation, dict):
            errors.append("discourse.revocation must be a mapping")
        else:
            if revocation.get("status") != "revoked":
                errors.append("discourse.revocation.status must be revoked")
            if not isinstance(revocation.get("reason"), str) or not revocation["reason"].strip():
                errors.append("discourse revocation requires a reason")
            if not isinstance(revocation.get("authority"), str) or not revocation["authority"].strip():
                errors.append("discourse revocation requires an authority")

    claim_ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, dict):
            errors.append("each discourse claim must be a mapping")
            continue
        claim_id = claim.get("id")
        if not isinstance(claim_id, str) or not claim_id or claim_id in claim_ids:
            errors.append("discourse claim ids must be unique non-empty strings")
        else:
            claim_ids.add(claim_id)
        if claim.get("kind") not in CLAIM_KINDS:
            errors.append(f"claim {claim_id!r} kind must be one of {sorted(CLAIM_KINDS)}")
        if not isinstance(claim.get("reason"), str) or not claim["reason"].strip():
            errors.append(f"claim {claim_id!r} requires a reason")

    unresolved = False
    for objection in objections:
        if not isinstance(objection, dict):
            errors.append("each discourse objection must be a mapping")
            continue
        objection_id = objection.get("id")
        if objection.get("claim") not in claim_ids:
            errors.append(f"objection {objection_id!r} references an unknown claim")
        status = objection.get("status")
        if status not in OBJECTION_STATUSES:
            errors.append(f"objection {objection_id!r} has an invalid status")
        if not isinstance(objection.get("reason"), str) or not objection["reason"].strip():
            errors.append(f"objection {objection_id!r} requires a reason")
        if status == "addressed" and (not isinstance(objection.get("response"), str) or not objection["response"].strip()):
            errors.append(f"addressed objection {objection_id!r} requires a response")
        unresolved = unresolved or status == "unresolved"

    if event.get("status") == "stabilized":
        missing = sorted(set(affected) - set(participants))
        if missing:
            errors.append(f"stabilized discourse excludes affected roles: {', '.join(missing)}")
        if unresolved:
            errors.append("stabilized discourse cannot contain unresolved objections")
        if closure.get("status") != "accepted":
            errors.append("stabilized discourse requires accepted closure")
        if not isinstance(closure.get("reason"), str) or not closure["reason"].strip():
            errors.append("accepted discourse closure requires a reason")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_discourse.py <event.yaml>")
        return 2
    errors = validate(Path(sys.argv[1]))
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"VALID DISCOURSE {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
