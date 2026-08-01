---
name: recursive-codex-lite
description: Assess consequential project changes and document only the non-obvious reasoning that Git, CI, reviews, and repository policy do not already preserve. Use for changes with cross-component consequences, materially different alternatives, durable interpretive choices, costly recovery, or later decision-history value. Skip for routine fixes adequately explained by the diff, tests, commit, or pull request.
---

# Recursive Codex Lite

Use native project mechanisms first: `AGENTS.md` for conventions, Git for history and recovery,
worktrees or branches for isolation, CI for checks, and review or approvals for authority. Do not
reimplement or duplicate them.

## Decide whether a note is warranted

Create a relational change note only when at least one condition holds:

- the change alters relationships across components, roles, sources, or meanings;
- materially different approaches were plausible;
- the reason will not be evident from the diff and tests;
- recovery is costly, ambiguous, or depends on a decision that may later be questioned;
- the change opens, restricts, or defers important future possibilities.

Otherwise complete the task normally. Do not create a note, decision record, journal entry, or
variant exercise merely to satisfy this skill.

## Work with the project

1. Identify the request, current baseline, applicable repository guidance, and existing authority.
2. Use the project's normal branch, worktree, tests, CI, review, and approval mechanisms.
3. Consider alternatives only when they are materially different. Never manufacture a second
   variant for symmetry.
4. Review relational consequences: what the change enables, constrains, excludes, or postpones,
   and which downstream components or roles inherit those effects.
5. If a note is warranted, use [assets/change-note.md](assets/change-note.md). Prefer placing its
   content in the pull-request description. Create a repository file only when the reasoning must
   outlive the PR and the user authorizes that durable record.
6. Record validation evidence by reference, not duplication. Link or name the relevant tests,
   CI run, review, or source instead of copying logs.
7. Leave the final choice with the authority already provided by the project. This skill does not
   create a new authority layer.

## Keep the method subordinate

- Do not add schemas, validators, kernels, policies, hash chains, or enforcement code for the note.
- Do not protect the note with another note.
- Do not treat documentation completeness as evidence that the change is correct.
- Stop recording when the additional explanation costs more than its likely future use.
- When revisiting a note, mark whether it was actually useful. Prefer deleting or simplifying
  fields that repeatedly provide no value.

Report the completed work first. Mention relational consequences only when they change how the
user should understand, approve, recover, or continue the work.

