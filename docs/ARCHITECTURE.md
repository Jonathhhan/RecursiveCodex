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

- Add a domain in `domains/<name>.yaml`.
- Add deterministic domain checks to its `checks` list.
- Extend schemas compatibly using a new schema version.
- Add skills only when their workflow differs materially from the core skill.
