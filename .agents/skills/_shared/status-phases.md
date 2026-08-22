# Authority

`core-zero/project/state-machine.yaml` is the machine-readable lifecycle authority. This file is human guidance only and must remain subordinate to that state machine; route phases and runtime transition checks use the YAML contract.

The canonical feature lifecycle state machine for CoreZero.
The route registry and artifact checks define the maintained status contract. Write `- Phase:`
only through `status-set`, `skill-enter`, or `skill-exit`. Use exactly these phase
strings and follow the transition rules below.

# Why This File Exists

Phase strings are scattered across individual SKILL.md files and historically
differ slightly between them. This file is the single source of truth. Any skill
that transitions phase reads from this table, not from memory.

# Complexity Tiers (Canonical Vocabulary)

The canonical complexity scale is `Simple | Moderate | Complex`. All skills use
these three terms. Do not introduce alternate profile names.

# Phase Reference

Use these exact machine tokens in `status.md` (and equivalent metadata fields):

| Phase / State       | Set by              | Meaning                                                                | Suggested handoff  |
| ------------------- | ------------------- | ---------------------------------------------------------------------- | ------------------- |
| `Researching`       | `spec-research`     | Investigation is active                                                | —                   |
| `ResearchComplete`  | `spec-research`     | `analysis.md` is ready; root cause or brownfield map is written        | `spec-requirements` |
| `Specifying`        | `spec-requirements` | Spec authoring is active                                               | —                   |
| `SpecApproved`      | `spec-requirements` | `spec.md` is locked                                                    | `spec-plan`         |
| `Planning`          | `spec-plan`         | Technical design authoring is active                                   | `spec-tasks`        |
| `TaskPlanning`      | `spec-tasks`        | Task graph authoring is active                                         | —                   |
| `PlanApproved`      | `spec-tasks`        | `plan.md` and `tasks.md` are ready; first unblocked task is executable | `spec-implement`    |
| `Implementing`      | `spec-implement`    | Code work is active                                                    | —                   |
| `Verifying`         | `harness-verify`    | Verification is active                                                 | —                   |
| `Done`              | `harness-verify`    | Mechanical gate passed, alignment passed, post-ship sync complete      | —                   |

# Transition Rules

1. Forward only. A skill must not set a phase to an earlier state unless it is
   explicitly correcting a failed or stale state (e.g., reopening a spec after a
   planning blocker is discovered).

2. Set phase at skill start with `skill-enter`. The envelope writes the route
   `enter` token before judgment work begins (e.g., `spec-plan` sets `Planning`).

3. Approved/Done phase requires verification. A skill MUST NOT set
   `SpecApproved`, `PlanApproved`, or `Done` unless its own internal
   verification checklist passes. Setting the approved phase is the last act
   of the skill, not the first.

4. No phase skipping. `spec-implement` requires `PlanApproved`.
   `harness-verify` requires `Implementing` or a re-verify trigger.
   An agent must not skip phases to save time.

5. Re-entry is explicit. If implementation reveals a spec gap, the correct
   action is to return to `spec-requirements` (setting phase back to `Specifying`)
   with an explicit note in `status.md` explaining why. Silent re-entry is a Red Flag.

# Optional Phases

These tokens are written to `- Phase:` through `status-set` when work leaves the
happy path. They are legal machine states. Restore a core delivery token when
work resumes.

| Phase                 | Set by     | Meaning                                                                  |
| --------------------- | ---------- | ------------------------------------------------------------------------ |
| `NeedsClarification`  | `spec-requirements` | Spec blocked on external decision or missing info                 |
| `Blocked`             | Any skill  | Work is stalled on an external dependency; must name the blocker         |
| `Replanning`          | `spec-plan` / `spec-tasks` / `harness-verify` | Design or task graph must be revised before implementation resumes      |
| `ChangesRequested`    | `harness-verify` | Verification found issues                      |
| `Abandoned`           | Any skill  | Feature intentionally stopped                                           |

# Status File Sections

A minimal `status.md` must always contain:

```markdown
# Feature Status: <slug>

- Phase: [machine token from the route registry]
- Delivery profile: Simple | Moderate | Complex
- Status: Active | Blocked | Done
```


## Recovery protocol

When work becomes `Blocked`, record the reason, owner, evidence, review date,
and recommended handoff under `## Blocked Recovery` in `status.md`. Use
`NeedsClarification` for a missing product decision, `Blocked` for an external
dependency, `Replanning` when the design/task graph is invalidated, and
`ChangesRequested` when verification finds correctable defects. `Abandoned`
requires an archival summary and a Post-Ship Sync decision about reusable
lessons. Resume only through a legal machine transition; do not hand-edit the
token.
