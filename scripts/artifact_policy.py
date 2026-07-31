"""Installed artifact-validator registry and bounded resource policy."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from _mini_yaml import load

POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "artifact-policy.yaml"


@lru_cache(maxsize=1)
def policy() -> dict:
    value = load(POLICY_PATH)
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("invalid installed artifact policy")
    if not isinstance(value.get("validators"), dict) or not isinstance(value.get("limits"), dict):
        raise ValueError("artifact policy requires validators and limits")
    return value


def validator_path(identifier: str) -> Path:
    relative = policy()["validators"].get(identifier)
    if not isinstance(relative, str):
        raise ValueError(f"unregistered artifact validator: {identifier}")
    path = (Path(__file__).resolve().parents[1] / relative).resolve()
    if not path.is_file():
        raise ValueError(f"installed artifact validator is missing: {identifier}")
    return path


def resource_errors(root: Path, artifacts: list[dict]) -> list[str]:
    limits = policy()["limits"]
    errors: list[str] = []
    if len(artifacts) > limits["max_artifacts"]:
        errors.append("artifacts exceed max_artifacts")
    if len(artifacts) > limits["max_generated_checks"]:
        errors.append("artifacts exceed max_generated_checks")
    by_id = {item.get("id"): item for item in artifacts if isinstance(item, dict)}
    memo: dict[str, int] = {}
    def depth(identifier: str, active: set[str]) -> int:
        if identifier in memo: return memo[identifier]
        if identifier in active: return 0
        item = by_id.get(identifier, {})
        value = 1 + max((depth(dep, active | {identifier}) for dep in item.get("depends_on", []) if dep in by_id), default=0)
        memo[identifier] = value
        return value
    if any(depth(identifier, set()) > limits["max_dependency_depth"] for identifier in by_id):
        errors.append("artifact graph exceeds max_dependency_depth")
    for index, item in enumerate(artifacts):
        path = root / item.get("path", "") if isinstance(item, dict) else root
        if path.is_file() and path.stat().st_size > limits["max_artifact_bytes"]:
            errors.append(f"artifacts[{index}] exceeds max_artifact_bytes")
    return errors
