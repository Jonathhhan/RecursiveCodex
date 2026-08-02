---
name: recursive-codex-lite
description: Identify and preserve the smallest part of an AI-assisted decision that normal project records would lose. Use when a change selects one of at least two plausible options and Git, tests, issues, and review would not let a future maintainer reconstruct why that option was chosen and another was rejected or deferred. Skip when no plausible alternative existed or the selection reason is already recoverable.
---

# Reason-Loss Test

Use the project's existing mechanisms first. Repository guidance defines constraints and authority;
Git records the change and recovery path; tests and CI provide validation evidence; issues and
review hold discussion.

Before creating any additional record, verify both conditions:

1. At least two options were plausible when the decision was made.
2. The existing project history does not preserve why one was selected over the other.

If either condition is false, do not create a note. Otherwise ask:

> What is the smallest part of the selection reason a future maintainer could not reconstruct
> without this note?

If there is an answer, add the shortest sufficient note to the pull-request description, commit
body, issue, or other normal project record. Create a separate repository file only when the
reasoning must outlive those records and the user authorizes it.

Record only the missing decision residue:

- the selected option and the plausible alternative;
- the selection reason or constraint that is not recoverable elsewhere;
- the authority or decision status, only when that too is absent elsewhere.

Do not duplicate diffs, logs, test output, repository rules, or issue discussion. Do not add a
schema, validator, graph, journal, policy, or second note to protect the note. A complete record is
not evidence that the decision is correct.

When a note is encountered later, mark whether it was useful only if that observation can improve
or remove the practice. Stop using fields that repeatedly add no decision value.
