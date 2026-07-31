"""Load the installed trust-boundary policy shared by validators and controller."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from _mini_yaml import load

POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "trust-boundaries.yaml"


@lru_cache(maxsize=1)
def policy() -> dict:
    value = load(POLICY_PATH)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid installed trust-boundary policy")
    for key in ("critical", "high", "protected_outputs"):
        entries = value.get(key)
        if not isinstance(entries, list) or not all(isinstance(item, str) and item for item in entries):
            raise ValueError(f"trust-boundary policy {key} must be a string list")
    return value


def paths_for(key: str) -> set[str]:
    return {Path(item).as_posix().rstrip("/") for item in policy()[key]}


def overlaps(path: str, boundary: str) -> bool:
    path = Path(path).as_posix().rstrip("/")
    boundary = Path(boundary).as_posix().rstrip("/")
    return path == boundary or path.startswith(boundary + "/") or boundary.startswith(path + "/")


def risk_for_paths(paths: list[str]) -> str:
    if any(overlaps(path, item) for path in paths for item in paths_for("critical")):
        return "critical"
    if any(overlaps(path, item) for path in paths for item in paths_for("high")):
        return "high"
    return "low"
