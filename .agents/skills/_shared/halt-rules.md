## HALT Markers

Use `[:HALT ...]` markers to block progress on incomplete, ambiguous, or stale states:

| Marker | Meaning | Owning / Escalation Skill |
|---|---|---|
| `[:HALT NEEDS CLARIFICATION]` | Missing external decision or information | `/spec-requirements` |
| `[:HALT UNRESOLVED]` | Multiple failed attempts to resolve ambiguity | Escalate to user |
| `[:HALT ADR CONFLICT: ADR-NNN]` | Contested architecture decision or spec violates ADR | `/spec-adr` |
| `[:HALT SECURITY: <desc>]` | Security-sensitive path without evidence | `/harness-verify` |
| `[:HALT INCONCLUSIVE]` | Evidence too sparse; cannot determine root cause or tight loop | `/spec-research` |
| `[:HALT STALE — spec amended <date>]` | Spec changed after plan/tasks approved; requires re-planning | `/spec-plan` |
| `[:HALT SYNC REQUIRED]` | Post-ship memory sync heading is missing; block `Done` | `/context-memory` |

All HALT markers must be resolved before phase completion. Task mutations (`task-start`, `task-done`, `task-block`) are mechanically blocked while any `[:HALT` substring exists in `spec.md`, `plan.md`, or `tasks.md`.
