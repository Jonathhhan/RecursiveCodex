# Project audit

The unified audit command inspects the complete locally available Recursive Codex state:

```powershell
python scripts/recursive_codex.py audit .
python scripts/recursive_codex.py audit . --json
```

An installed command wrapper may expose the same interface as `recursive-codex audit`.

## Hard failures

The command returns a non-zero status for:

- invalid project or domain contracts;
- invalid individual change events;
- duplicate event or decision identifiers;
- missing event-to-decision or decision-to-event references;
- missing structured baseline events;
- cycles among structured event baselines;
- invalid generative or autopoietic journal sequences and hash chains.

## Warnings

Legacy baseline labels from the early repository history are reported as warnings because they predate path-addressed event edges. A dirty workspace is also a warning: it matters to reproducibility but does not make the stabilized graph internally invalid.

Warnings remain visible in text and JSON output. They are never silently treated as validated graph edges.

## Boundary

Audit success establishes structural integrity of the inspected records. It does not establish the truth of research claims, validity of premises, philosophical adequacy, linguistic quality, or artistic value. Those judgments remain governed by the active domain and declared authority.
