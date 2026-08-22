# CoreZero Skills

All 11 CoreZero skills are peer-level direct entrypoints. `/starter-init` is recommended only for an untailored repository. A common delivery route is `/spec-research` when needed, then `/spec-requirements`, `/spec-plan`, `/spec-tasks`, `/spec-implement`, `/harness-verify`, and optional `/context-memory`.

## Invocation

1. Select a skill such as `/spec-plan` and read its `SKILL.md`.
2. Feature-bound delivery skills (`spec-research` through `harness-verify`) enter with `python3 core-zero/scripts/core/cli.py skill-enter --skill <name> [--feature <slug>] [--task <T-NNN>] --intent "<request>"`.
   That loads the route, opens or resumes the session, and writes the enter state to `status.md` when the route declares one.
   `starter-init`, `context-memory`, `harness-maintain`, `spec-adr`, and `spec-testing-scenario` have no enter/exit tokens; follow their `SKILL.md` and use context or session commands as documented.
   Inspect selection and omissions with `context-explain`; use
   `--add-source <repo-relative-path>` only for a focused expansion.
3. Follow the procedure. Use `status-set` only for an explicit exception state (`Blocked`, `Replanning`, `NeedsClarification`). Do not hand-edit `- Phase:`.
4. Use the named task, artifact, and verification commands while judging.
5. Exit a feature-bound delivery skill with `python3 core-zero/scripts/core/cli.py skill-exit --skill <name> --feature <slug> [--handoff <next>]`.

`references/context-routes.yaml` is the only routing authority. It contains all 11 named CoreZero skills. There is no phase fallback and no generated routing cache.

## Common delivery route

```text
/starter-init (recommended only for an untailored repository)
  → /spec-research (when behavior or root cause is unknown)
  → /spec-requirements
  → /spec-plan
  → /spec-tasks
  → /spec-implement
  → /harness-verify
  → /context-memory (when durable lessons need promotion)
```

This is a suggested handoff path, not a hierarchy. `/spec-adr`, `/spec-testing-scenario`, and `/harness-maintain` are also direct CoreZero entrypoints. Shared contracts live in `_shared/` (artifact, halt, handoff, verification, and decision rules). For optional repository documentation, technical contracts, diagrams, architecture surveys, and pattern analysis, see [`../EXTERNAL_SKILLS.md`](../EXTERNAL_SKILLS.md).

## Runtime commands

- Bootstrap: `init`, `status`
- Envelope: `skill-enter`, `skill-exit`, `status-set`
- Context: `context-pack`, `context-load`, `context-explain`
- Sessions: `session-start`, `session-checkpoint`, `session-end`
- Tasks: `task-check`, `task-start`, `task-done`, `task-block`
- Delivery checks: `phase-check`, `artifact-check`, `verify`
- Diagnostics: `doctor`, `gate-check`, `gate-list`, `provider-list`, `provider-check`, `provider-run`, `memory-audit`, `memory-gate`
- Decisions: `adr-generate`
