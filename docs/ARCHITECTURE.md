# Architecture

Recursive Codex separates four layers:

1. **Core protocol** — operation classes, recursive cycle, change events, authority gates, and closure.
2. **Domain profile** — vocabulary, source rules, protected paths, roles, and checks for one field or project.
3. **Project contract** — selects a domain and binds it to a repository.
4. **Execution record** — change events and accepted decisions produced during work.

The core never decides what counts as a valid argument, safe deployment, admissible source, or successful artwork. Domains provide those criteria. Validators check declared structure and evidence; they do not certify truth.

## Collective model

A collective is an advisory review graph, not a sovereign agent. Roles operate independently and return attributed findings. The authority declared by the project contract selects, rejects, delegates, or defers.

## Extension points

## Effective checks

The autonomous controller executes one effective ordered check list. Domain-profile checks run first, declared artifact instances run second, and project-contract checks run third, all inside the same isolated candidate workspace. Every group is bound into proposal attestation and stabilization evidence.

Check identifiers are unique across both scopes. A project check cannot shadow or replace a domain check. The domain supplies invariant criteria; the project may add repository-specific criteria.

Validation of check declarations does not count as their execution. `validate_project.py` rejects malformed or ambiguous declarations, while the autonomous controller executes the effective list before promotion.
A domain may publish an `artifact_contract` containing its installed validator and artifact kind. The project binds concrete `{id, path}` instances through `artifacts`. Their effective check IDs are `artifact-<id>` and cannot shadow domain or project checks.


- Add a domain in `domains/<name>.yaml`.
- Add deterministic domain checks to its `checks` list.
- Extend schemas compatibly using a new schema version.
- Add skills only when their workflow differs materially from the core skill.
