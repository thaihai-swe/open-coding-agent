# CoreBase SpecHarness Context and Session Router

CoreBase SpecHarness is skills-first: users invoke any of the 11 CoreBase SpecHarness skills directly. `/starter-init` is recommended only when the installed repository has not been tailored.

```bash
python3 corebase-specharness/scripts/core/cli.py skill-enter --skill <name> --feature <slug> --task <T-NNN> --intent "<request>"
python3 corebase-specharness/scripts/core/cli.py skill-exit --skill <name> --feature <slug> --handoff <next>
```

Featureless skills omit `--feature`. Sessions live at `.corezero/sessions/<slug>/session.md`.

## Authorities

- `skills/<name>/SKILL.md` — agent procedure.
- `references/context-routes.yaml` — named route metadata and bounded source selection.
- `references/tool-providers-registry.json` — optional provider inventory.
- `corebase-specharness/project/state-machine.yaml` — kit-owned lifecycle, extended via `lifecycle_overrides`.
- `corebase-specharness/project/tool-providers.md` — adopter provider selection.
- `artifacts/features/<slug>/` — delivery state and evidence (`tasks.md` canonical; `tasks.json` generated sidecar).

## Mechanical commands

- `init`, `status`, `status-set`
- `skill-enter`, `skill-exit`
- `context-pack`, `context-load`, `context-explain`
- `session-start`, `session-checkpoint`, `session-end`
- `task-check`, `task-start`, `task-done`, `task-block`
- `phase-check`, `artifact-check`, `verify`
- `doctor`, `gate-check`, `gate-list`
- `provider-list`, `provider-check`, `provider-run`
- `memory-audit`, `memory-gate`, `adr-generate`

The runtime does not select skills, infer project gates, install providers, or
promote memory. A user request becomes a named-skill `skill-enter`: route
lookup, session open, then a budgeted context pack. Token estimates use
`cl100k_base` when `tiktoken` is installed, otherwise `len(text) / 4.0`. The
pack never dumps the repository. Shared procedure contracts live in
`skills/_shared/`. See `CONTEXT_AND_MEMORY.md` for the request path and
budget math.
