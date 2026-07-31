"""Finite calculus-of-indications model for autopoietic observations."""

from __future__ import annotations

import json


def mark(content: list[dict] | None = None) -> dict:
    return {"mark": content or []}


def _key(node: dict) -> str:
    return json.dumps(node, sort_keys=True, separators=(",", ":"))


def normalize(space: list[dict]) -> list[dict]:
    """Apply calling (deduplication) and crossing (double-mark cancellation)."""
    if not isinstance(space, list) or not all(isinstance(node, dict) for node in space):
        raise ValueError("form space must be a list of marks")
    reduced: list[dict] = []
    for node in space:
        if set(node) != {"mark"} or not isinstance(node["mark"], list):
            raise ValueError("form nodes must contain exactly one mark")
        content = normalize(node["mark"])
        if len(content) == 1 and set(content[0]) == {"mark"}:
            # Crossing: a mark around one mark returns the inner content.
            reduced.extend(content[0]["mark"])
        else:
            reduced.append(mark(content))
    unique = {_key(node): node for node in reduced}
    return [unique[key] for key in sorted(unique)]


def indication(space: list[dict]) -> str:
    return "unmarked" if normalize(space) == [] else "marked"


def distinction(marked: str, unmarked: str, indicated: str) -> dict:
    if not all(isinstance(item, str) and item.strip() for item in (marked, unmarked)):
        raise ValueError("distinction sides must be non-empty strings")
    if marked == unmarked:
        raise ValueError("distinction sides must differ")
    if indicated not in {"marked", "unmarked"}:
        raise ValueError("indicated side must be marked or unmarked")
    expression = [mark()] if indicated == "marked" else []
    return {
        "marked": marked,
        "unmarked": unmarked,
        "indicated": indicated,
        "expression": expression,
        "value": indication(expression),
    }


def reentry(source: dict, side: str) -> dict:
    if side not in {"marked", "unmarked"}:
        raise ValueError("re-entry side must be marked or unmarked")
    return {
        "marked": source["marked"],
        "unmarked": source["unmarked"],
        "indicated": source["indicated"],
        "expression": source["expression"],
        "value": source["value"],
        "reentry": {"source": source["id"], "side": side},
    }
