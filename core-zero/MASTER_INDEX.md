# CoreZero Context and Session Router

CoreZero is skills-first: users invoke any of the 11 CoreZero skills directly. `/starter-init` is recommended only when the installed repository has not been tailored.

```bash
python3 core-zero/scripts/core/cli.py skill-enter --skill <name> --feature <slug> --task <T-NNN> --intent "<request>"
python3 core-zero/scripts/core/cli.py skill-exit --skill <name> --feature <slug> --handoff <next>
```

Featureless skills omit `--feature`. Sessions live at `.corezero/sessions/<slug>/session.md`.

## Authorities

- `skills/<name>/SKILL.md` — agent procedure.
- `references/context-routes.yaml` — named route metadata and bounded source selection.
- `references/tool-providers-registry.json` — optional provider inventory.
- `core-zero/project/state-machine.yaml` — kit-owned lifecycle (`schema_version: 1`), extended via `lifecycle_overrides`.
- `core-zero/project/tool-providers.md` — adopter provider selection.
- `artifacts/features/<slug>/` — delivery state and evidence (`tasks.md` canonical; `tasks.json` generated sidecar).

## Mechanical commands

- `skill-enter`, `skill-exit`, `status-set`
- `context-pack`, `context-load`, `context-explain`
- `session-start`, `session-checkpoint`, `session-end`
- `task-check`, `task-start`, `task-done`, `task-block`
- `phase-check`, `artifact-check`, `verify`
- `doctor`, `gate-check`, `gate-list`
- `provider-list`, `provider-check`, `provider-run`
- `memory-audit`, `memory-gate`, `adr-generate`

The runtime does not select skills, infer project gates, install providers, or
promote memory. It compiles an inspectable, bounded local context pack from
the named route plus automatic local evidence retrieval; it never dumps global
repository context. Shared procedure contracts live in `skills/_shared/`.
