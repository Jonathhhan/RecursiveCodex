# Hyperspace generation

A hyperspace is a declared multidimensional possibility space. Each dimension contains named options and optional numeric scores. Scores express local selection preferences; they are not evidence of truth.

The generator offers two materially different strategies:

- `exhaustive` emits the complete Cartesian product and refuses to exceed the node budget.
- `frontier` expands one dimension per iteration, orders candidates deterministically, and retains at most the node budget. This is the default for bounded autonomous exploration.

An optional `exclusions` list declares relationally incompatible partial combinations. Each exclusion is a non-empty mapping from dimension IDs to option IDs. A branch is removed as soon as all choices named by an exclusion are present, and each iteration records how many generated states were excluded.

An exclusion may instead declare a conditional exception with `when` and `unless` mappings:

```json
{"when": {"form": "open"}, "unless": {"response": "echo"}}
```

This excludes an open form unless its response is an echo. Evaluation waits until every dimension referenced by both mappings is available, preventing a branch from being removed before its exception can be observed. Legacy mapping exclusions remain supported.

```powershell
python scripts/generate_hyperspace.py examples/hyperspace-improvisation.json --max-nodes 12 --output hyperspace.json
```

The output records every iteration, generated and retained counts, the theoretical complete size, and the final retained possibilities. Domain profiles remain responsible for defining meaningful dimensions and admissible scoring criteria.
