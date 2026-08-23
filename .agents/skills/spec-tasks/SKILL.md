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
| **Reads** | `corebase-specharness/rules/code-design.md`, `spec.md`, `plan.md`, `status.md` |
| **Writes** | Required: `tasks.md`. Optional: `status.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-tasks --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-tasks --feature <slug> --handoff spec-implement` |
| **Entry** | Directly invokable peer skill; handoff may suggest `/spec-implement` |

## Overview

Converts the approved technical design in `plan.md` into `artifacts/features/<slug>/tasks.md`. It answers: what is the smallest safe implementation sequence, and what task does implementation start with?

Derives canonical task graph nodes (`T-NNN`), maps acceptance criteria (`Covers: AC-*`), sets dependency links (`Depends on: T-NNN`), and locks the `PlanApproved` state machine phase gate.

Each task is a **tracer bullet**: a narrow but complete path that is demoable or verifiable on its own, cutting through every layer the task touches (data, logic, interface, tests). Avoid horizontal layer-only tasks ("schema only", "API only") unless a layer is a genuine prerequisite with no observable behavior yet.

## When to Use & Invocation Triggers

- **When to Use**:
  - Creating the executable task breakdown from an approved `plan.md`.
  - Re-sequencing or updating task dependencies after a design iteration.
- **Triggers**: `task`, `breakdown`, `estimate`, `milestone`

## Execution Modes & Profiles

| Strategy / Mode | Condition / Trigger | Primary Purpose & Outputs |
|---|---|---|
| `mvp-first` | Multi-story feature; default strategy | Complete P1 user story and its tests before P2; each story has an independent ship gate |
| `incremental` | Slices are sequential or tightly coupled | Linear phase execution: P1 -> P2 -> P3 -> Polish |
| `parallel-team` | Subsystem slices have clean boundaries | Foundational setup completes first, then story tasks run concurrently |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/spec.md`, `artifacts/features/<slug>/plan.md`, `artifacts/features/<slug>/status.md`, `corebase-specharness/rules/code-design.md`, `corebase-specharness/rules/ponytail.md`.
- **Writes**:
  - `artifacts/features/<slug>/tasks.md` (`T-NNN`, `Covers: AC-*`, `Depends on: T-NNN`)
  - `artifacts/features/<slug>/status.md` via `skill-enter` (`TaskPlanning`) and `skill-exit` (`PlanApproved`)
- **Session State**: Updates `.corezero/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-tasks --feature <slug> --intent "<request>"`.
   - Confirm `plan.md` exists. Do not hand-edit `- Phase:`.

2. **User Story Decomposition & Task Breakdown**:
   - Create `artifacts/features/<slug>/tasks.md` using `references/tasks-template.md`.
   - Break work into **tracer bullet** vertical slices: each slice delivers end-to-end verifiable behavior.
   - *Wide Refactor Exception*: For wide mechanical refactors where a single edit breaks many call sites at once, sequence as **expand–contract**:
     1. Expand: add the new form beside the old so nothing breaks.
     2. Migrate: migrate call sites in blast-radius batches, each batch its own ticket blocked by expand.
     3. Contract: delete the old form in a final ticket blocked by all migrate batches.
   - For `Moderate`/`Complex` multi-story features: Group tasks under Setup/Foundational, User Story P1 (`US1`), User Story P2 (`US2`), and Polish.
   - For every task item:
     - Assign canonical ID format: `T-001`, `T-002`, etc. (never `TASK-*`).
     - Specify task goal, target module-map file paths, entry proof (failing test command), exit proof, and `Covers: AC-*`.
     - Set dependency edges via `Depends on: T-NNN` (or leave blank for linear order).
     - Target 2–4 hour increments per task.

3. **Traceability & Granularity Quiz Checkpoint**:
   - Verify every requirement (`REQ-*`) and acceptance criterion (`AC-*`) in `spec.md` is mapped to at least one task.
   - Check granularity: does any task cover more than one vertical slice? Are blocking edges strictly necessary?

4. **Task Graph Validation**:
   - Run `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>` to verify zero dependency cycles or broken IDs.
   - Run `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>` to determine the first ready task. Record it under `## Resume Notes` in `tasks.md`.
   - (Optional state changes): Use `python3 corebase-specharness/scripts/core/cli.py task-start/task-done/task-block --feature <slug> --task <T-NNN>`.

5. **Definition of Ready & Phase Gate Handoff**:
   - Apply `../spec-plan/references/definition-of-ready.md`.
   - Run `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill spec-tasks`. Fix any failures.
   - Mark `Plan approved` `[x]`, then run `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-tasks --feature <slug> --handoff spec-implement`.

## Anti-Patterns & Red Flags

- **Legacy ID Formatting**: Using `TASK-001` instead of canonical `T-001` (breaks task graph parser).
- **Design After Tasks**: Inventing new architecture or scope during task breakdown.
- **Missing AC Traceability**: Creating tasks without `Covers: AC-*` linkage.
- **Fake Parallelism**: Marking tasks `[P]` despite shared mutable files or contract dependencies.

## Core Rules

- **Canonical Task IDs**: Every task MUST use `T-NNN` (e.g. `T-001`).
- **No Spec Re-opening**: Stick strictly to approved requirements and technical design.
- **Cycle-Free Graph**: Task dependency graph MUST pass `python3 corebase-specharness/scripts/core/cli.py task-check`.
- **Verifiable Increments**: Every task MUST specify an explicit exit proof command.
