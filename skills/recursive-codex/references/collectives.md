# Collectives

A collective is a temporary arrangement of independent review roles around one change.

## Role contract

Each role declares:

- `id`: stable identifier;
- `mandate`: the question it alone examines;
- `inputs`: primary artifacts it may use;
- `output`: findings, objections, and proposals;
- `authority: advisory`.

Useful neutral roles include consistency reviewer, counterexample reviewer, provenance reviewer, operational reviewer, and domain specialist.

## Rules

1. Do not give reviewers the desired conclusion.
2. Keep findings attributed to their roles.
3. Do not convert agreement into truth or disagreement into failure.
4. Route selection through the domain profile's declared authority.
5. Record rejected and deferred findings when they materially affect future work.
