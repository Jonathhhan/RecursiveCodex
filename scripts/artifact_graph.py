"""Domain-neutral dependency ordering for declared project artifacts."""

from __future__ import annotations


def dependency_errors(artifacts: list[dict]) -> list[str]:
    identifiers = {
        item.get("id") for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    errors: list[str] = []
    edges: dict[str, list[str]] = {}
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            continue
        identifier = artifact.get("id")
        dependencies = artifact.get("depends_on", [])
        if not isinstance(dependencies, list) or not all(
            isinstance(item, str) and bool(item.strip()) for item in dependencies
        ):
            errors.append(f"artifacts[{index}].depends_on must be a string list")
            continue
        if len(dependencies) != len(set(dependencies)):
            errors.append(f"artifacts[{index}].depends_on entries must be unique")
        for dependency in dependencies:
            if dependency not in identifiers:
                errors.append(
                    f"artifacts[{index}].depends_on references unknown artifact: {dependency}"
                )
        if isinstance(identifier, str):
            edges[identifier] = dependencies

    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(identifier: str) -> None:
        if state.get(identifier) == 2:
            return
        if state.get(identifier) == 1:
            start = stack.index(identifier)
            errors.append("artifact dependency cycle: " + " -> ".join(stack[start:] + [identifier]))
            return
        state[identifier] = 1
        stack.append(identifier)
        for dependency in edges.get(identifier, []):
            if dependency in edges:
                visit(dependency)
        stack.pop()
        state[identifier] = 2

    for identifier in edges:
        visit(identifier)
    return errors


def ordered_artifacts(artifacts: list[dict]) -> list[dict]:
    """Return stable dependency-first order; declarations break independent ties."""
    errors = dependency_errors(artifacts)
    if errors:
        raise ValueError("; ".join(errors))
    by_id = {item["id"]: item for item in artifacts}
    emitted: set[str] = set()
    result: list[dict] = []

    def emit(identifier: str) -> None:
        if identifier in emitted:
            return
        for dependency in by_id[identifier].get("depends_on", []):
            emit(dependency)
        emitted.add(identifier)
        result.append(by_id[identifier])

    for artifact in artifacts:
        emit(artifact["id"])
    return result
