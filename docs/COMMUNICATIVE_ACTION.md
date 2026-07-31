# Communicative-action domain

The optional `communicative-action` profile adds a discourse gate without changing the domain-neutral core. Projects adopting it record a `discourse` mapping in each governed change event.

The record distinguishes affected roles, actual participants, reasoned validity claims, objections and responses, and discourse closure. Claims are classified as `factual`, `normative`, `expressive`, or `technical` so that a technical score cannot silently stand in for a normative justification.

A stabilized event must represent every affected role among its participants, contain no unresolved objection, and give an explicit reason for accepted closure. Addressed objections require responses. Deferred or contested closure remains representable but cannot be mislabeled as stabilized.

A later loss of normative force is represented by an optional `discourse.revocation` mapping with `status: revoked`, a reason, and the authority responsible for revocation. Revocation does not rewrite the accepted closure or make the historical discourse structurally invalid; it declares that the evidence may no longer authorize normative goals.

Run the gate with:

```powershell
python scripts/validate_discourse.py <event.yaml>
```

This validates the declared structure of participation and justification. It cannot establish sincere consent, equal power, or freedom from coercion; those remain substantive review questions.
