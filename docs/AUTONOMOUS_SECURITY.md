# Autonomous controller security boundary

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
