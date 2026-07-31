# Recursive Codex repository rules

This repository implements a domain-neutral Codex workflow. Do not import a domain's concepts into the core unless the behavior can be stated without that vocabulary.

Before structural changes:

1. read `docs/ARCHITECTURE.md` and `docs/GENEALOGY.md`;
2. identify core, domain, plugin, and example impacts separately;
3. preserve authority and provenance boundaries;
4. add or update tests for validators and templates;
5. run `python -m unittest discover -s tests -v` and both validators.

Collectives widen review; they do not decide truth by vote. A decision is accepted only by the authority declared in the active domain profile.
