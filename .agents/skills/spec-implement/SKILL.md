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
| **Reads** | `corebase-specharness/rules/security.md`, `corebase-specharness/rules/code-design.md`, `spec.md`, `plan.md`, `tasks.md` |
| **Writes** | Optional: project source, `tasks.md`, `status.md`, `session-extracts.md`. Session: `.corezero/sessions/<slug>/session.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-implement --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py task-start --feature <slug> --task <T-NNN>`, `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-implement --feature <slug> --task <T-NNN>`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-implement --feature <slug> --handoff harness-verify` |
| **Entry** | Directly invokable peer skill; handoff may suggest `/harness-verify` |

## Overview

Performs the coding work by executing task items in `artifacts/features/<slug>/tasks.md` one at a time. It answers: can I complete the selected task and prove it without inventing new scope?

Enforces task locking (`python3 corebase-specharness/scripts/core/cli.py task-start`), pre-flight baseline checks, TDD red-green loop at pre-agreed public seams, mechanical verification (`python3 corebase-specharness/scripts/core/cli.py verify`), and evidence-backed completion (`python3 corebase-specharness/scripts/core/cli.py task-done`).

## When to Use & Invocation Triggers

- **When to Use**:
  - Executing code changes for an approved task list (`tasks.md`).
  - Resuming work on an in-progress task.
- **Triggers**: `implement`, `code`, `build`, `deliver`

## Execution Modes & Profiles

| Mode | Task State | Primary Purpose & Actions |
|---|---|---|
| `task-execution` | `Not Started` | Lock task via `task-start`, run pre-flight baseline, implement code, run `verify`, log evidence via `task-done` |
| `mid-task-resumption` | `In Progress` | Read last session note, re-run proving command; restart task if baseline fails |
| `task-blocked` | `Blocked` | Record blocker via `task-block`, update session notes, escalate to user or route to `/spec-plan` |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/spec.md`, `artifacts/features/<slug>/plan.md`, `artifacts/features/<slug>/tasks.md`, `corebase-specharness/rules/security.md`, `corebase-specharness/rules/code-design.md`, `corebase-specharness/rules/ponytail.md`.
- **Writes**:
  - Project source code and test files
  - `artifacts/features/<slug>/status.md` via `skill-enter` / `skill-exit` (`Implementing`)
  - `artifacts/features/<slug>/tasks.md` (updated status, exit proofs, completion timestamps)
  - `artifacts/features/<slug>/session-extracts.md` (recording `[CANDIDATE]` lessons)
- **Session State**: Updates `.corezero/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-implement --feature <slug> --intent "<request>"`.
   - Run `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill spec-implement`.
   - *Spec-Staleness Check*: If `spec.md` modification date is newer than `plan.md` approval date, stamp `[:HALT STALE — spec amended after plan approved]` on plan/tasks and route to `/spec-plan`.

2. **Task Selection & Locking**:
   - Run `python3 corebase-specharness/scripts/core/cli.py task-check --feature <slug>` to select the next ready unblocked task (`T-NNN`).
   - Lock task: Run `python3 corebase-specharness/scripts/core/cli.py task-start --feature <slug> --task <T-NNN>`. (Never edit checkboxes by hand).
   - Reload a task-scoped pack before editing: `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-implement --feature <slug> --task <T-NNN> --intent "<request>"`. Do not pass `--full`. The compiler omits full `tasks.md` and injects only the active task plus its direct dependencies.
   - If `task-check` finds no ready `T-NNN`, halt. Do not start coding against the full task list.

3. **Pre-Flight Baseline & TDD Implementation**:
   - Run the task's validation/proving command once in terminal before editing to establish a baseline.
   - Confirm the task's public seam from `plan.md` / the proof command. Read `references/tdd-loop.md`.
   - Follow the red-green loop: write the failing proof at the confirmed seam first, then write only enough production code to pass it.
   - Banned anti-patterns (see `references/tdd-loop.md`): implementation-coupled tests, tautological tests, and horizontal slicing (all tests before any implementation).
   - If the required seam is missing, stamp `[:HALT STALE — spec amended after plan approved]` or route to `/spec-plan`, do not invent an internal mock seam.
   - Implement code and tests strictly within the task boundary, following `code-design.md` and `ponytail.md`.
   - Embed spec traceability markers (`REQ-*`/`AC-*`/`T-NNN`).

4. **Semantic Review & Mechanical Validation**:
   - Verify semantic intent (LLM-as-Judge check on diff).
   - Re-run local task proof command.
   - Run `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill spec-implement` for mechanical gate validation.

5. **Logging, Lesson Extraction & Task Close**:
   - Record validation proof: Run `python3 corebase-specharness/scripts/core/cli.py task-done --feature <slug> --task <T-NNN> --evidence "<fresh proof summary>"`.
   - (If blocked): Run `python3 corebase-specharness/scripts/core/cli.py task-block --feature <slug> --task <T-NNN> --note "<reason>"`.
   - Record candidate lessons: Append non-trivial design decisions as `[CANDIDATE]` entries to `artifacts/features/<slug>/session-extracts.md`.
   - If tasks remain, loop back to Step 2 and reload `context-load` with the next `--task`. Do not re-run `skill-enter`. When all tasks complete, run `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-implement --feature <slug> --handoff harness-verify`.

## Anti-Patterns & Red Flags

- **Vibe Coding**: Writing code without locking a target `T-NNN` task first via `task-start`.
- **Silent Scope Creep**: Refactoring adjacent unrelated files during a task.
- **Skipping Pre-Flight**: Editing code before running the pre-flight baseline test.
- **Fake Proofs**: Running `task-done` with empty or unverified `--evidence`.

## Core Rules

- **Strict Task Scoping**: Every edit MUST be scoped to a locked `T-NNN` task.
- **Task-Scoped Context**: After `task-start`, coding turns MUST use `context-load --task T-NNN` so the full `tasks.md` is omitted.
- **Mandatory Task Proof**: `task-done` REQUIRES non-empty `--evidence`.
- **Ponytail Simplicity**: Maintain lazy senior dev mindset — use native features before adding dependencies.
- **Context Eviction**: Summarize raw terminal gate logs and evict them from context. Do not pass `--full` unless the pack is known stale.
