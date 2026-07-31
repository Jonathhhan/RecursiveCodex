# Change events

Change events make intervention history reconstructable. They are not activity logs.

- `baseline` identifies the recoverable state before the intervention.
- `scope` states which paths may change and which are protected.
- `provenance` separates sources, current state, proposals, and decisions.
- `relations` records actual cross-component effects.
- `possibilities` makes consequences explicit without assuming that more options are better.
- `variants` records materially executed alternatives and selection reasons.
- `authority` distinguishes `pending`, `accepted`, `delegated`, and `not_required` decisions.
- `validation` records evidence, not philosophical or domain truth.
- `status` moves from `proposed` to `tested` to `stabilized`.

Use schema `schemas/change-event.schema.json`. Stabilization requires an accepted/not-required decision, a recovery strategy, at least one passed validation, and no open blocking uncertainty.
