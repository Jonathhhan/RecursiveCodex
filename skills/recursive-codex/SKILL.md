---
name: recursive-codex
description: Run complex Codex project changes as recursive, reviewable work with explicit authority, provenance, alternatives, relational consequences, optional independent reviewer roles, and closure checks. Use for architecture changes, manuscript or research revisions, cross-file reorganizations, audits, contested integrations, or requests to work recursively, compare variants, use a collective, or document a change event.
---

# Recursive Codex

Treat each substantial change as a revision of an already organized project state.

## Load the project contract

1. Read `.recursive-codex/project.yaml` from the project root.
2. Read the referenced domain profile completely.
3. Resolve authority, protected paths, required sources, vocabulary constraints, and checks.
4. Distinguish current state, source material, proposal, reviewer finding, and accepted decision.
5. Stop if a required authority decision is absent.

If no project contract exists, use `../../scripts/init_project.py` from the plugin root and ask only for domain choices that materially change the contract.

## Classify one primary operation

- `local_update`: a bounded change with local consequences;
- `composition`: combine materials into a new arrangement;
- `revision`: return to an accepted or stabilized state;
- `reorganization`: change relationships among multiple components;
- `audit`: inspect and report without changing project files.

Use the wider classification when effects cross components. Do not hide structural work inside `local_update`.

## Run the recursive cycle

1. **Connect:** establish request, baseline, sources, and constraints.
2. **Organize:** map dependencies, authority, roles, and protected paths.
3. **Update:** make the smallest sufficient change.
4. **Review relations:** inspect downstream effects and unexpected exclusions.
5. **Critique:** test contradictions, counterexamples, omissions, and scope drift.
6. **Stabilize:** validate and accept only with the declared authority.

Return to an earlier step whenever review changes the problem.

## Use variants and collectives

When multiple materially different solutions are plausible, execute at least two comparable variants before selection. Do not create cosmetic alternatives.

Use two or three independent reviewer roles for contested structural work or when the user requests a collective. Give each reviewer the artifacts and a distinct review mandate, not an expected conclusion. Preserve disagreement. Reviewers recommend; the declared authority decides.

Read [collectives.md](references/collectives.md) when creating or interpreting reviewer roles.

## Record a change event

For every `revision`, `reorganization`, or substantial `composition`, create an event from `../../templates/change-event.yaml` before editing. Complete it after validation.

The event must record:

- baseline and allowed/protected scope;
- provenance and relevant decisions;
- actual changes and affected relations;
- opened, restricted, and deferred possibilities;
- variants, reviewer findings, decision status, and recovery path;
- validation evidence and final status.

Run `scripts/validate_change_event.py <event>` before stabilization. Read [change-events.md](references/change-events.md) for field semantics.

## Close the work

Run every check declared by the domain profile plus:

```powershell
python <plugin-root>/scripts/validate_project.py <project-root>
python <plugin-root>/scripts/validate_change_event.py <event-file>
```

Do not equate validator success with domain truth. Report what changed, affected relations, opened/restricted/deferred options, accepted/open decisions, and checks.
