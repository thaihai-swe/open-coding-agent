# Authority

`corebase-specharness/project/state-machine.yaml` is the machine-readable lifecycle authority. This file is a human cheat-sheet only.

Write `- Phase:` only through `status-set`, `skill-enter`, or `skill-exit`. Use these exact tokens.

## Phase Tokens

| Token | Set by | Meaning | Suggested handoff |
|---|---|---|---|
| `Researching` | `spec-research` | Investigation active | — |
| `ResearchComplete` | `spec-research` | `analysis.md` ready | `spec-requirements` |
| `Specifying` | `spec-requirements` | Spec authoring active | — |
| `SpecApproved` | `spec-requirements` | `spec.md` locked | `spec-plan` |
| `Planning` | `spec-plan` | Design authoring active | `spec-tasks` |
| `TaskPlanning` | `spec-tasks` | Task graph authoring | — |
| `PlanApproved` | `spec-tasks` | `plan.md` + `tasks.md` ready | `spec-implement` |
| `Implementing` | `spec-implement` | Code work active | — |
| `Verifying` | `harness-verify` | Verification active | — |
| `Done` | `harness-verify` | Gate + alignment + post-ship complete | — |

## Exception Tokens (`status-set`)

| Token | Meaning |
|---|---|
| `NeedsClarification` | Missing product decision |
| `Blocked` | External dependency; name the blocker |
| `Replanning` | Design/task graph invalidated |
| `ChangesRequested` | Verification found correctable defects |
| `Abandoned` | Feature stopped; archive reusable lessons |

## Transition Rules

1. Forward only, except explicit correction of a failed or stale state.
2. Set phase at skill start via `skill-enter`.
3. `SpecApproved`, `PlanApproved`, and `Done` require the skill's verification checklist; they are the last act, not the first.
4. No phase skipping. `spec-implement` requires `PlanApproved`. `harness-verify` requires `Implementing` or a re-verify trigger.
5. Re-entry is explicit. Spec gaps return to `spec-requirements` with a `status.md` note.

Complexity scale is `Simple | Moderate | Complex`. Do not invent alternate profile names.
