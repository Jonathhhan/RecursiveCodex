# Autonomous controller security boundary

## Declarative trust boundary

`config/trust-boundaries.yaml` is the installed, self-protected classification shared by project validation and proposal risk derivation. Enforcement, audit, graph, validator, schema, and executable autopoiesis paths cannot be overwritten by ephemeral check output. Changes to critical paths require external authority.

Artifact validators are selected by identity from `config/artifact-policy.yaml`; domain profiles cannot execute an arbitrary validator path. The same policy bounds artifact count, generated checks, dependency depth, and artifact byte size.

After isolated candidate checks pass, promotion performs two additional bindings:

1. the applied workspace is validated in a fresh Python process using the applied enforcement code;
2. its bounded snapshot digest must equal the validated candidate digest.

Thus a proposal cannot validate changed enforcement code only through stale imports in the long-running parent.

## Constituting authority

`config/bootstrap.yaml` records the one-time repository-owner constitution of the critical boundary at commit `f36d7ad350038c7c1089ca8da9b63feb663df292`. Autonomous self-amendment is forbidden. A mandatory critical set embedded in `trust_policy.py` means the YAML policy may extend but cannot remove the bootstrap, controller, policy, or manifest from critical protection.

The exact bootstrap commit has a successful public [GitHub Actions CI run](https://github.com/Jonathhhan/RecursiveCodex/actions/runs/30673087859). This external run complements rather than replaces local event evidence.


The autonomous child is a proposal generator, not a repository writer. It runs read-only and returns one patch. The parent validates paths and authority before evaluating that patch.

Declared checks use structured argument vectors. String commands and shell interpretation are invalid project contracts:

```yaml
checks:
  - id: unit-tests
    command:
      - python
      - -m
      - unittest
      - discover
      - -s
      - tests
    ephemeral_outputs: []
```

The parent copies the project to a temporary candidate directory without `.git`, controller runtime files, bytecode caches, or symbolic links. It applies and stabilizes the proposal there, then runs each check with `shell=False`. A content snapshot is compared before and after every check. Changes outside `ephemeral_outputs` reject the proposal. Ephemeral outputs are never promoted and may not overlap contracts, events, decisions, controller or validator code, schemas, or protected paths. The candidate directory is discarded in every case.

Only after candidate validation succeeds and the real workspace is confirmed unchanged does the parent apply the patch to the real project. If finalization fails, reverse-patch success and the restored workspace snapshot are mandatory. Failure of either condition raises a hard controller error.

An atomic `.recursive-codex/runtime/controller.lock` contains the PID, UTC start time, and operating-system process identity. A second controller cannot enter the workspace while the lock exists. `run_autonomous.py <project> --unlock-stale --stale-after 3600` is an explicit operator action: it removes the lock only after the minimum age and only when the recorded process identity is no longer active. Malformed, young, or actively owned locks fail closed and are never silently stolen.

## Proposal attestations

A proposal carries the selected goal, sorted patch paths, declared check IDs, risk level, recovery strategy, decision and event IDs, baseline commit, and a digest of every non-runtime workspace file. The parent supplies its baseline values before generation and compares the returned claims before candidate evaluation. It then compares IDs and recovery with the parsed candidate records. Any mismatch fails closed. `critical` risk cannot be accepted by the autonomous path.

## Trust limits

Candidate-copy isolation protects repository contents from undeclared check writes. It is not an operating-system sandbox and cannot roll back network calls, subprocess effects, or writes outside the candidate directory. Check definitions live in the protected owner-controlled project contract and are trusted capabilities. Unattended use therefore requires the owner to configure deterministic local checks; stronger hostile-code isolation needs an external container or OS sandbox.

`recursive-codex-system` is a local process role recognized by the project contract. It is not a cryptographic identity or an independently authenticated authority. Structural agreement among an event, decision, and implementation proves consistency only, not external legitimacy.

The project contract, active domain binding, controller, validator, and genealogy are protected from autonomous proposals in this repository. Changes to those trust anchors require an externally authorized maintenance operation.
