# Generative kernel

The generative kernel adds persistent strategic memory without replacing the existing autonomous safety controller. It stores hash-chained JSON Lines events for goals, capabilities, attempts, and outcomes, then reconstructs state deterministically.

Journal schema 2 assigns every event a monotone `sequence`, the preceding `previous_hash`, and an `event_hash` over canonical JSON. Replay verifies the complete chain and nondecreasing timestamps before interpreting any goal. Append operations use an exclusive sibling lock and flush each record to disk. Payloads cannot override chain metadata.

Goals have strategic, tactical, or operational levels, explicit priority, and required capabilities. Selection prefers priority, then wider level, then stable identifier order. Failed strategies remain attached to later selections. A completed goal produces quiescence when no pending goal remains; unavailable capabilities produce an explicit blocked state.

```powershell
python scripts/generative_kernel.py memory.jsonl add-goal improve-writing --level strategic --priority 10 --requires text-generator
python scripts/generative_kernel.py memory.jsonl capability text-generator --status available
python scripts/generative_kernel.py memory.jsonl select
```

Goals default to technical claims. A goal declared with `--claim-kind normative` must reference a discourse event that is stabilized, passes `validate_discourse.py`, and contains at least one normative claim:

```powershell
python scripts/generative_kernel.py memory.jsonl add-goal revise-policy --level strategic --priority 20 --claim-kind normative --discourse-event examples/communicative-event.yaml --requires discourse-validator
```

The reference is resolved relative to the process working directory. On admission the kernel records its SHA-256 content hash; replay requires the current bytes to match that bound hash before reapplying the discourse gate. Missing, modified, malformed, proposed, contested, revoked, or non-normative evidence is therefore an invariant violation rather than a selectable goal. Existing journal goals remain technical by default and retain their prior replayed state shape.

A revoked discourse record retains its stabilized status and accepted historical closure. Its validated `discourse.revocation` marker records the reason and responsible authority, while the kernel treats that evidence as inadmissible for new and replayed normative goals.

The autonomous controller uses `.recursive-codex/runtime/generative-kernel.jsonl` when that journal contains events. Before each child cycle it replays the journal and either supplies the selected goal and its failed strategies as strategic context, reports missing capabilities as blocked, or stops at strategic quiescence. A rejected proposal records a failed attempt. A proposal stabilized by the parent records a successful attempt and a completing outcome.

An absent or empty runtime journal preserves the controller's existing repository-derived candidate selection. Goals enter the journal only through explicit kernel events; the controller does not invent strategic goals or reinterpret failed validation as permission to relax an invariant.

Runtime memory is deliberately outside proposal patches. It survives proposal rollback, while repository events and decisions remain subject to the normal proposal, validation, and stabilization gates.

The kernel records declared operational memory. Its discourse gate checks structural admission evidence; it does not prove genuine consent, undistorted communication, truth, or unlimited authority.
## Legacy migration and audit limits

Schema-1 journals require an explicit one-time migration:

```powershell
python scripts/generative_kernel.py memory.jsonl migrate
```

Migration writes a temporary complete schema-2 chain, flushes it, atomically replaces the legacy file, and revalidates it. Every migrated event includes `legacy_event_hash`, the SHA-256 identity of its original record.

The chain detects altered records, insertion, middle deletion, reordering, duplicate positions, and backward timestamps. It is tamper-evident rather than tamper-proof: it does not authenticate a writer, an attacker who rewrites the whole file can recompute hashes, and removal of the final suffix cannot be proven without an externally anchored head hash.
