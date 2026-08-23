---
id: skill-spec-tasks
name: spec-tasks
description: "Turn an approved technical design into a sequenced, traceable, executable task graph using canonical T-NNN IDs."
tags: ['spec', 'planning', 'tasks']
triggers: ['task', 'breakdown', 'estimate', 'milestone']
---
# Spec Tasks

## At a Glance

| | |
|---|---|
| **Reads** | `code-design.md`, `spec.md`, `plan.md`, `status.md` |
| **Writes** | Required: `tasks.md`. Optional: `status.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-tasks --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-tasks --feature <slug> --handoff spec-implement` |
| **Entry** | Direct peer skill; handoff may suggest `/spec-implement` |

## Overview

Convert `plan.md` into `tasks.md`: `T-NNN` nodes, `Covers: AC-*`, `Depends on: T-NNN`, then lock `PlanApproved`. Each task is a tracer bullet — a narrow complete path, not a layer-only slice.

## When to Use & Invocation Triggers

- **When to Use**: executable breakdown from approved `plan.md`; re-sequence after design change.
- **Triggers**: `task`, `breakdown`, `estimate`, `milestone`

## Execution Modes & Profiles

| Mode | Condition | Output |
|---|---|---|
| `mvp-first` | Multi-story; default | P1 story + tests before P2; each story has a ship gate |
| `incremental` | Sequential / coupled slices | P1 → P2 → P3 → Polish |
| `parallel-team` | Clean subsystem boundaries | Setup first, then concurrent story tasks |

## I/O & Artifact Protocol

- **Reads**: `spec.md`, `plan.md`, `status.md`, `code-design.md`, `ponytail.md`.
- **Writes**: `tasks.md`; `status.md` (`TaskPlanning` → `PlanApproved`).
- **Session**: `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-tasks --feature <slug> --intent "<request>"`.
   - Omit `--full` unless compacted, new chat on existing feature, reload requested, or pack stale. See `skills/_shared/context-loading.md`.
   - Confirm `plan.md` exists. Do not hand-edit `- Phase:`.

2. **Breakdown**:
   - Create `tasks.md` via `references/tasks-template.md`.
   - Vertical tracer-bullet slices with end-to-end verifiable behavior.
   - Wide mechanical refactors use expand–contract: (1) add new beside old, (2) migrate call sites in batches, (3) delete old last.
   - Moderate/Complex: group under Setup, US1/P1, US2/P2, Polish.
   - Each task: `T-001` IDs (never `TASK-*`); goal; module-map paths; entry proof (failing command); exit proof; `Covers: AC-*`; `Depends on: T-NNN`; 2–4 hour target.

3. **Traceability**:
   - Every `REQ-*` and `AC-*` maps to ≥1 task.
   - Check granularity: one vertical slice per task; blocking edges only when necessary.

4. **Graph validation**:
   - `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>` — zero cycles, valid IDs.
   - Record first ready task under `## Resume Notes`.
   - Optional: `python3 corebase-specharness/scripts/core/cli.py task-start/task-done/task-block --feature <slug> --task <T-NNN>`.

5. **Ready & handoff**:
   - Apply `../spec-plan/references/definition-of-ready.md`.
   - `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill spec-tasks`.
   - Mark `Plan approved` `[x]`, then `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-tasks --feature <slug> --handoff spec-implement`.

## Anti-Patterns & Red Flags

- `TASK-001` instead of `T-001`.
- Inventing architecture during breakdown.
- Tasks without `Covers: AC-*`.
- Fake `[P]` on tasks that share mutable files.

## Core Rules

- IDs MUST be `T-NNN`.
- No spec re-opening.
- Graph MUST pass `task-check`.
- Every task MUST name an exit proof command.
