---
name: recursive-codex-lite
description: Execute consequential changes as a reversible cycle from situated material through selection, an actual candidate, consequence review, and authorized stabilization. Use when a change has cross-component effects, materially different alternatives, durable interpretive choices, costly recovery, or later decision-history value. Skip routine fixes adequately explained by the diff, tests, commit, or pull request.
---

# Recursive Codex Lite

Use native project mechanisms first: repository guidance for constraints, Git for history and
recovery, branches or worktrees for isolation, CI for checks, and review for authority. This skill
organizes a change; it does not duplicate those mechanisms.

## Decide whether a note is warranted

Create a relational change note only when at least one condition holds:

- the change alters relationships across components, roles, sources, or meanings;
- materially different approaches were plausible;
- the reason will not be evident from the diff and tests;
- recovery is costly, ambiguous, or depends on a decision that may later be questioned;
- the change opens, restricts, or defers important future possibilities.

Otherwise complete the task normally. Do not create a note, decision record, journal entry, or
variant exercise merely to satisfy this skill.

## Execute one reversible cycle

1. **Situate the material.** Identify the request, baseline, provenance, existing decisions,
   protected parts, repository guidance, and authority. Treat files, sources, tests, and prior
   versions as already shaped material rather than neutral input.
2. **Classify the intervention.** Distinguish exploration, integration, correction under an
   unchanged condition, revision of a stabilized condition, and reorganization of relations among
   several conditions. Do not call every modification a revision. Scale isolation, review, and
   documentation to the intervention's relational depth rather than its line count.
3. **Select and defer.** State what the candidate takes up, preserves, cuts, and leaves open.
   Produce alternatives only when genuinely different selections or arrangements remain viable.
4. **Execute the smallest sufficient candidate.** Make the change in the project's normal isolated
   workspace. Do not bundle adjacent reforms.
5. **Inspect the actual result.** Read or run the candidate as produced. Compare it with the
   baseline and check tests, representation, references, and affected relations. Treat unexpected
   effects as findings; do not infer correctness from successful execution.
6. **Countercheck.** Ask whether the finding was prearranged by the method, is merely a tool or
   presentation effect, survives a description without this skill's vocabulary, and already
   exists in project history. A framework must not use compliance with its own rules as evidence
   for its validity.
7. **Stabilize, revise, or reject.** Let the project's declared authority decide when the choice is
   consequential or equally strong alternatives remain. Preserve rejected or deferred material
   only when it has plausible future value.
8. **Return the consequences.** Report what the result actually enables, constrains, excludes, or
   postpones and which downstream components or roles inherit those effects.

If durable reasoning is warranted, use [assets/change-note.md](assets/change-note.md). Prefer its
content in the pull-request description. Create a repository record only when it must outlive the
PR and the user authorizes it. Cite validation evidence instead of copying logs.

## Keep the method subordinate

- Do not add schemas, validators, kernels, policies, hash chains, or enforcement code for the note.
- Do not protect the note with another note.
- Do not treat documentation completeness as evidence that the change is correct.
- Do not translate project-specific philosophical or artistic vocabulary into universal software
  claims. Preserve the distinction between a genealogical source and a domain-neutral procedure.
- Stop recording when the additional explanation costs more than its likely future use.
- When revisiting a note, mark whether it was actually useful. Prefer deleting or simplifying
  fields that repeatedly provide no value.

Report the completed work first. Mention relational consequences only when they change how the
user should understand, approve, recover, or continue the work.
