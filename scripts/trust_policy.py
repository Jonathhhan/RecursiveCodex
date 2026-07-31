"""Load the installed trust-boundary policy shared by validators and controller."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from _mini_yaml import load

MANDATORY_CRITICAL = {
    "config/bootstrap.yaml",
    "config/trust-boundaries.yaml",
    "scripts/run_autonomous.py",
    "scripts/trust_policy.py",
}
BOOTSTRAP_PATH = Path(__file__).resolve().parents[1] / "config" / "bootstrap.yaml"

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
    authorities = value.get("authorities")
    if not isinstance(authorities, dict) or not all(isinstance(key, str) and isinstance(item, str) and item for key, item in authorities.items()):
        raise ValueError("trust-boundary policy authorities must be a string mapping")
    critical = {Path(item).as_posix().rstrip("/") for item in value["critical"]}
    missing = MANDATORY_CRITICAL - critical
    if missing:
        raise ValueError(f"trust-boundary policy missing mandatory critical paths: {sorted(missing)}")
    return value



@lru_cache(maxsize=1)
def bootstrap() -> dict:
    value = load(BOOTSTRAP_PATH)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid bootstrap record")
    if value.get("established_by") != "repository-owner":
        raise ValueError("bootstrap must be established by repository-owner")
    commit = value.get("commit")
    if not isinstance(commit, str) or len(commit) != 40 or any(char not in "0123456789abcdef" for char in commit):
        raise ValueError("bootstrap commit must be a full Git hash")
    if value.get("autonomous_self_amendment") != "forbidden":
        raise ValueError("bootstrap must forbid autonomous self amendment")
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
