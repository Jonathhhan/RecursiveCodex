# Recursive Codex

Recursive Codex is a domain-configurable infrastructure for recursive, reviewable, reversible, and autonomously stabilized knowledge production.

Software development is one application, not the universal model. Art, language, logic, philosophy, research, and other practices can define their own objects, validity dimensions, checks, and authorities without importing their vocabulary into the neutral core.

It separates a small technical core from project-specific concepts. A philosophy manuscript, software architecture, research program, or artistic process can supply its own domain profile without turning one domain's vocabulary into a universal theory.

## Core cycle

```text
connect → organize → update → review relations → critique → stabilize
```

The cycle is recursive: review can reopen the problem, demand another variant, or block stabilization.

## What is implemented

- a Codex skill under `skills/recursive-codex/`;
- domain profiles with explicit authority, protected paths, vocabulary, and checks;
- structured change events with provenance, alternatives, consequences, and decision status;
- optional collectives of independent roles without majority truth;
- first-class profiles for art, language, logic, philosophy, research, communicative action, and autopoiesis;
- auditable JSON sidecars for linguistic variants, logical derivations, and philosophical arguments;
- a shared artifact validator that checks declared structure without claiming domain truth;
- deterministic initialization and validation scripts;
- isolated autonomous proposal checks with structured commands, side-effect detection, verified rollback, and workspace locking;
- a neutral example domain and unit tests.

## Quick start

```powershell
python scripts/init_project.py C:\path\to\project --domain research
python scripts/validate_project.py C:\path\to\project
python scripts/validate_change_event.py C:\path\to\project\.recursive-codex\events\0001-example.yaml
```


## Unified audit

```powershell
python scripts/recursive_codex.py audit .
```

The audit checks project and domain contracts, individual records, the event/decision graph, structured baselines, journal hash chains, and workspace state. See `docs/AUDIT.md`.
Then ask Codex to use `$recursive-codex` for a change, audit, revision, or reorganization.

## Repository layout

```text
.codex-plugin/plugin.json       Codex plugin manifest
skills/recursive-codex/         Agent workflow
schemas/                        Machine-readable contracts
templates/                      Project and event templates
domains/                        Reusable domain profiles
scripts/                        Initialization and validation
tests/                          Dependency-free test suite
```
Art, language, logic, and philosophy workflows are described in `docs/KNOWLEDGE_DOMAINS.md`.


The autonomous controller's security and trust boundary is documented in `docs/AUTONOMOUS_SECURITY.md`.

## Genealogy and scope

The architecture originated in the book project *Zur Kritik der Organisation von Anschlussmöglichkeiten*. Its technical procedures—provenance, variants, relational review, decision gates, and reversibility—are generalized here. The book's philosophical concepts and claims are not generalized with them. See `docs/GENEALOGY.md`.

## Development

```powershell
python -m unittest discover -s tests -v
python scripts/validate_project.py examples/minimal-project
```

No network access or third-party Python package is required.
