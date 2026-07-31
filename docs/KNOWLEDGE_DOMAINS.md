# Language, logic, and philosophy

Recursive Codex is not a software-development theory with optional writing features. It is a domain-neutral protocol for recursively producing and stabilizing inspectable operations. Software is one domain; art, language, logic, and philosophy supply different objects, criteria, and authorities.

## Shared protocol

Every domain uses the same neutral sequence:

```text
state -> proposal -> variants -> relational review -> critique -> authorized selection -> validation -> stabilization -> history
```

Determinism applies to declared inputs, operation order, provenance, validation, authority, and recorded selection. It does not mean that prose quality, logical premises, or philosophical truth are reduced to one numerical score.

## Art

The `art` profile organizes media, materials, transformations, variants, situated experience, critique, provenance, and curatorial selection. A work may be generated autonomously, but stabilization remains bound to declared artistic authority rather than a universal novelty or preference score.

The artifact sidecar records intention and selection without reducing the work to those descriptions. Material and experiential effects can exceed what the record says; the record makes the production and decision process inspectable.

## Language

The `language` profile treats a text as an operation carrying semantic commitments into a situation and audience. Recursive work generates variants, compares meaning and pragmatic effect, criticizes exclusions and ambiguity, then stabilizes one version under editorial authority.

A language artifact records the selected text, audience, register, semantic commitments, considered variants, and selection reason. This makes revision history inspectable without pretending that a validator can decide literary value.

## Logic

The `logic` profile separates formalization, derivation, and countermodel search. An artifact states premises, conclusion, selected logic, derivation, and countermodel status. Validation checks that these responsibilities are explicit; a domain-specific prover may be added as a project check.

Syntactic validity and premise truth remain separate. Changing the formalization is recorded when it changes the problem rather than merely its notation.

## Philosophy

The `philosophy` profile organizes theses, concepts, reasons, sources, objections, responses, and authorized judgments. It distinguishes source claims from interpretation and inference. Every recorded objection requires a response, but neither structural completeness nor consensus establishes philosophical truth.

Philosophical autonomy therefore means autonomous organization of distinctions and reasons under an explicit authority. It does not authorize the technical controller to settle metaphysical or normative validity silently.

## Artifact validation

The common sidecar validator accepts JSON artifacts:

```powershell
python scripts/validate_domain_artifact.py art path/to/art.json
python scripts/validate_domain_artifact.py language path/to/language.json
python scripts/validate_domain_artifact.py logic path/to/argument.json
python scripts/validate_domain_artifact.py philosophy path/to/thesis.json
```


Projects bind artifact instances in `.recursive-codex/project.yaml`:

```yaml
artifacts:
  - id: principal-thesis
    path: artifacts/thesis.json
```

The active domain supplies the validator and kind. The controller derives an `artifact-principal-thesis` check automatically and executes it between domain checks and project checks in the isolated candidate workspace. Missing files, unsafe paths, absent domain contracts, and effective check-ID collisions fail project validation.
