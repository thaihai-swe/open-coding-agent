---
id: skill-spec-implement
name: spec-implement
description: "Execute implementation work task-by-task. Uses the approved spec, plan, and task list to drive code changes with strict status tracking and validation."
tags: ['spec', 'implementation', 'delivery']
triggers: ['implement', 'code', 'build', 'deliver']
---
# Spec Implement

## At a Glance

| | |
|---|---|
| **Reads** | `security.md`, `code-design.md`, `spec.md`, `plan.md`, `tasks.md` |
| **Writes** | Optional: project source, `tasks.md`, `status.md`, `session-extracts.md`. Session: `.corebase-specharness/sessions/<slug>/session.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-implement --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py task-start --feature <slug> --task <T-NNN>`, `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-implement --feature <slug> --task <T-NNN>`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-implement --feature <slug> --handoff harness-verify` |
| **Entry** | Direct peer skill; handoff may suggest `/harness-verify` |

## Overview

Execute `tasks.md` one locked task at a time. Prove each task without inventing scope. Enforces `task-start`, TDD at public seams, `verify`, and `task-done` with evidence.

## When to Use & Invocation Triggers

- **When to Use**: coding an approved `tasks.md`; resuming an in-progress task.
- **Triggers**: `implement`, `code`, `build`, `deliver`

## Execution Modes & Profiles

| Mode | Task State | Actions |
|---|---|---|
| `task-execution` | `Not Started` | `task-start` → baseline → implement → `verify` → `task-done` |
| `mid-task-resumption` | `In Progress` | Re-run proof; restart if baseline fails |
| `task-blocked` | `Blocked` | `task-block`, note, escalate or `/spec-plan` |

## I/O & Artifact Protocol

- **Reads**: `spec.md`, `plan.md`, `tasks.md`, `security.md`, `code-design.md`, `ponytail.md`.
- **Writes**: project source/tests; `status.md` (`Implementing`); `tasks.md` status/proofs; `session-extracts.md` `[CANDIDATE]` lessons.
- **Session**: `.corebase-specharness/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-implement --feature <slug> --intent "<request>"`.
   - Omit `--full` unless compacted, new chat on existing feature, user asked to reload, or pack is stale. See `skills/_shared/context-loading.md`.
   - `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill spec-implement`.
   - If `spec.md` is newer than `plan.md` approval, stamp `[:HALT STALE — spec amended after plan approved]` and route to `/spec-plan`.

2. **Task Selection & Locking**:
   - `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>` → next ready `T-NNN`.
   - `python3 corebase-specharness/scripts/core/cli.py task-start --feature <slug> --task <T-NNN>`. Never edit checkboxes by hand.
   - `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-implement --feature <slug> --task <T-NNN> --intent "<request>"`. Omit `--full` in the same uncompacted chat. Compiler injects only the active task + direct deps.
   - If no ready `T-NNN`, halt. Do not code against the full list.

3. **Baseline & TDD**:
   - Run the task proof command once before editing.
   - Confirm public seam from `plan.md` / proof command. Read `references/tdd-loop.md`.
   - Red-green: failing proof at the seam, then only enough code to pass.
   - Banned: implementation-coupled tests, tautological tests, horizontal slicing.
   - Missing seam → `[:HALT STALE — spec amended after plan approved]` or `/spec-plan`. Do not invent a mock seam.
   - Stay inside the task boundary. Follow `code-design.md` and `ponytail.md`. Embed `REQ-*`/`AC-*`/`T-NNN`.

4. **Review & Validation**:
   - Semantic check on the diff.
   - Re-run local proof.
   - `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill spec-implement`.

5. **Close**:
   - `python3 corebase-specharness/scripts/core/cli.py task-done --feature <slug> --task <T-NNN> --evidence "<fresh proof summary>"`.
   - Blocked: `python3 corebase-specharness/scripts/core/cli.py task-block --feature <slug> --task <T-NNN> --note "<reason>"`.
   - Append `[CANDIDATE]` lessons to `session-extracts.md`.
   - More tasks → Step 2 + `context-load --task`. Do not re-run `skill-enter`. All done → `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-implement --feature <slug> --handoff harness-verify`.

## Anti-Patterns & Red Flags

- Coding without `task-start` on a `T-NNN`.
- Refactoring unrelated files.
- Editing before the baseline proof.
- `task-done` with empty or unverified `--evidence`.

## Core Rules

- Every edit MUST be scoped to a locked `T-NNN`.
- After `task-start`, coding turns MUST use `context-load --task T-NNN`.
- `task-done` REQUIRES non-empty `--evidence`.
- Native features before new dependencies.
- Summarize and evict raw gate logs. Pass `--full` only after compact, new chat, reload request, or stale pack.
