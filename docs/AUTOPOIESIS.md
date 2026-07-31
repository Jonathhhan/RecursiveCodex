# Autopoiesis as a domain interpretation

Recursive Codex can be interpreted through Niklas Luhmann's account of autopoiesis, but the interpretation belongs to a domain profile rather than to the domain-neutral core.

## Translation into the workflow

| Systems-theoretical term | Recursive Codex operationalization |
| --- | --- |
| Operation | A change event that connects to an existing project state. |
| Autopoietic reproduction | Valid operations produce the conditions and records to which later operations may connect. |
| Operational closure | Only operations admitted by the project's own contract, validators, and authority can alter stabilized state. |
| Structural coupling | Prompts, source files, tools, and test results perturb the workflow without themselves becoming its decisions. |
| Self-observation | Relation review and critique inspect distinctions made by prior operations. |
| Memory | Stabilized events and accepted decisions condense expectations for later work. |

## Two-layer architecture

The safety controller remains a domain-neutral governance and execution layer. The experimental domain module at `domains/autopoiesis/kernel.py` models a separate operational sequence:

1. `perturbation-recorded` registers an environmental signal without granting it operative force.
2. `observation-produced` reconnects that signal through a previously drawn and indicated form.
3. `tension-formed` relates observations to an internal expectation and discrepancy.
4. `goal-generated` is accepted only when its complete content equals the kernel's deterministic derivation from an open tension.
5. `outcome-integrated` closes the generated connection and changes the conditions for later derivation.

A perturbation therefore cannot directly become a goal. The hash-chained operation journal records the internal transformations that make an Anschluss operation admissible. When no open tension remains, this layer reaches quiescence.

The domain profile binds the experimental journal to `.recursive-codex/runtime/autopoiesis.jsonl`. Example:

```powershell
python domains/autopoiesis/kernel.py .recursive-codex/runtime/autopoiesis.jsonl distinguish form-1 --marked system --unmarked environment --indicated marked
python domains/autopoiesis/kernel.py .recursive-codex/runtime/autopoiesis.jsonl perturb review-1 --source owner-review --signal "security displaced generation"
python domains/autopoiesis/kernel.py .recursive-codex/runtime/autopoiesis.jsonl observe observation-1 --perturbation review-1 --form form-1 --description "the operation history selects safeguards more often than new connections"
python domains/autopoiesis/kernel.py .recursive-codex/runtime/autopoiesis.jsonl form-tension tension-1 --observations observation-1 --expectation "operations reproduce further operations" --discrepancy "goals remain externally supplied" --priority 90 --level strategic
python domains/autopoiesis/kernel.py .recursive-codex/runtime/autopoiesis.jsonl generate
```

## Audited execution bridge

`domains/autopoiesis/bridge.py` closes the technical feedback cycle without collapsing the two layers. Export copies only goals recorded by a valid `goal-generated` operation. The execution goal stores that operation's journal hash, and the autopoietic journal stores a receipt containing the execution-event hash. Repeated synchronization is idempotent; a conflicting goal identifier or mismatched receipt fails closed.

Completed execution outcomes return through the bridge only as `perturbation-recorded`. They remain `unobserved` and cannot produce another goal until an internal observation and tension operation reconnects them.

```powershell
python domains/autopoiesis/bridge.py .recursive-codex/runtime/autopoiesis.jsonl .recursive-codex/runtime/generative-kernel.jsonl export
python domains/autopoiesis/bridge.py .recursive-codex/runtime/autopoiesis.jsonl .recursive-codex/runtime/generative-kernel.jsonl import
python domains/autopoiesis/bridge.py .recursive-codex/runtime/autopoiesis.jsonl .recursive-codex/runtime/generative-kernel.jsonl sync
```

## Boundary of the analogy

The implementation does not establish that Recursive Codex is a social system in Luhmann's theoretical sense. In Luhmann's account, social systems reproduce communication through communication. Recursive Codex instead processes technical artifacts under a configured workflow. The profile therefore guides observation and design without converting theoretical similarity into identity.

## Bounded cycle scheduler

`domains/autopoiesis/cycle.py` orders one feedback cycle. Without `--execute` it stops at `execution-ready`. With `--execute` it invokes exactly one controller cycle, imports any resulting outcome, and stops at `observation-required` when new perturbations exist.

```powershell
python domains/autopoiesis/cycle.py .recursive-codex/runtime/autopoiesis.jsonl .recursive-codex/runtime/generative-kernel.jsonl .
python domains/autopoiesis/cycle.py .recursive-codex/runtime/autopoiesis.jsonl .recursive-codex/runtime/generative-kernel.jsonl . --execute
```

The explicit observation boundary is constitutive, not an implementation gap: an execution result cannot describe its own significance for the observing system. A later observation must select a distinction and description before another tension can form. The scheduler therefore coordinates time without pretending that orchestration itself supplies self-observation.

Scheduler states are `quiescent`, `blocked`, `execution-ready`, `controller-failed`, `cycle-complete`, and `observation-required`. Every invocation is bounded to at most one controller operation.

## Calculus of indications

The form layer operationalizes selected constructions from George Spencer-Brown's *Laws of Form*. `distinction-drawn` records two different sides, indicates one side, and creates a finite marked or unmarked expression. Normalization applies calling by collapsing repeated identical marks and crossing by cancelling a mark around one mark. `form-reentered` explicitly reintroduces a recorded form on one of its sides while retaining its source identity.

An observation references a form identifier. It can no longer smuggle an undeclared distinction into free text. A second-order selection observation likewise names the form through which the earlier selection is currently observed.

```powershell
python domains/autopoiesis/kernel.py memory.jsonl distinguish form-1 --marked stable --unmarked changed --indicated marked
python domains/autopoiesis/kernel.py memory.jsonl reenter form-2 --source form-1 --side marked
```

This finite implementation does not claim to reproduce every mathematical or epistemological consequence of *Laws of Form*. It supplies an explicit grammar for drawing, indicating, reducing, and re-entering forms inside the technical operation model.

## Tractarian representation boundary

The proposition layer in `domains/autopoiesis/propositions.py` separates drawing a form from saying something testable through it. A `state-of-affairs-configured` operation declares objects and their possible relations. `proposition-formed` supplies a one-to-one picture mapping that covers those objects. `proposition-tested` records `confirmed`, `refuted`, or `undetermined` together with evidence.

An `observation-produced` operation must now reference both a form and a proposition. The operational chain is therefore:

`form -> possible state of affairs -> proposition/picture -> observation -> tension -> generated goal`

This is a constrained technical use of the picture theory in Wittgenstein's *Tractatus Logico-Philosophicus*: it makes the representational commitments of an observation inspectable. It does not assert that arbitrary repository sentences possess a complete logical form.

`representation-limit-observed` records that no admissible operational test has been declared for a subject. `silence-entered` may then connect to that limit without creating a tension or goal. In this implementation, silence is not missing output; it is a replayable refusal to turn an untestable metaphysical attribution into a technical fact.

Example operation sequence:

```text
state-of-affairs-configured(world-1, [system, goal], system-selects-goal)
proposition-formed(prop-1, world-1, "The system selects a goal", complete picture)
proposition-tested(test-1, prop-1, confirmed, journal evidence)
observation-produced(obs-1, perturbation-1, form-1, prop-1)
```


## Second-order observation and deliberate quiescence

An open tension need not become a goal. `continuation-deferred` records an internally attributed reason for refusing continuation and moves that tension to `deferred`; derivation then reaches quiescence when no other open tension remains.

After generation, `selection-observed` classifies the system's own selection as `reproduction`, `variation`, or `reorganization` under an explicit distinction. At least two such observations can support `expectation-condensed`. Active condensed expectations become part of later generated goal identities, so learning changes the structural context of selection rather than merely accumulating successful answers.

```powershell
python domains/autopoiesis/kernel.py memory.jsonl defer pause-1 --tension tension-1 --reason "continuation would only repeat the established distinction"
python domains/autopoiesis/kernel.py memory.jsonl observe-selection selection-1 --goal connection-id --mode variation --form form-1 --description "implementation changed while the relation remained stable"
python domains/autopoiesis/kernel.py memory.jsonl condense-expectation expectation-1 --observations selection-1 selection-2 --expectation "prefer reorganization after repeated local variation"
```

Autonomy means that the workflow selects its next admissible operation using its own contract and history. It does not mean independence from an environment or permission to rewrite its own authority. Environmental events can trigger or perturb another cycle; they cannot bypass provenance, protected scope, validation, or stabilization gates.

## Consequence for autonomy

Optimization is secondary. A cycle may improve a declared measure, but autopoietic continuation requires only that another admissible operation can connect. A system that maximizes a metric by deleting its authority or provenance conditions has interrupted, rather than improved, this implementation of reproduction.

## Fully autonomous mode

A project becomes fully autonomous when its contract declares `authority.final_decision: recursive-codex-system`. In that mode the workflow may generate goals from failed checks, contradictions, deferred possibilities, and relational effects; create and execute variants; write its own attributed decision; validate the selected change; stabilize it; and use the resulting state as the baseline for another operation.

No human acceptance is required for individual decisions in this mode. Prompts remain environmental perturbations rather than commands that bypass internal selection.

Full autonomy does not mean absence of constraints. The system must reproduce the invariants that constitute its identity: project contract, provenance boundary, protected paths, validation gates, recovery records, and resource limits. It reaches quiescence when it can derive no further admissible operation. It must stop on an invariant violation or exhausted runtime budget rather than reinterpret failure as permission.

The bridge transfers admissible operations between journals but does not change controller authority or bypass proposal validation. Continuous scheduling of `generate`, `sync`, controller execution, and renewed observation remains an orchestration concern rather than permission for the domain layer to rewrite the neutral core.
