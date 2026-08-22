# Context, Memory, and Providers

CoreZero compiles bounded project context from one explicit named-skill route,
then performs budgeted local evidence retrieval for the active intent and task.
It does not fall back to a phase matrix or dump the repository into the model.
Intent-matched domain packs (`glossary.md` `triggers`) join the pack as
`Should` sources, and retrieved excerpts redact detected secrets.

```bash
python3 core-zero/scripts/core/cli.py context-pack --skill spec-plan --feature <slug> --intent "design the change" --json
python3 core-zero/scripts/core/cli.py context-load --skill spec-plan --feature <slug> --intent "design the change" --json
python3 core-zero/scripts/core/cli.py context-explain --skill spec-plan --feature <slug> --intent "design the change" --json
```

Sessions live under `.corezero/sessions/<slug>/`. Durable memory remains adopter-owned Markdown under `core-zero/memories/` and `core-zero/project/`. `/context-memory` triages `[CANDIDATE]` lessons; `memory-audit` and `memory-gate` are read-only diagnostics.

Each context pack includes source paths, selection reasons, provenance, trust
labels, token estimates, and omitted-source reasons. Use
`--add-source <repo-relative-path>` only for a focused expansion; paths outside
the repository and policy-excluded paths are rejected. When
`retrieval.pinnable_sources` is configured, the added path must also match one
of its repository-relative glob patterns.

Optional providers are configured in `core-zero/project/tool-providers.md`. Use `provider-list` and `provider-check` to inspect selection and local availability. Provider setup, authentication, indexing, and MCP query execution remain explicit adopter or agent actions.
