# Tasks

## Metadata

- Feature/profile:
- Plan approved date:

## Implementation Strategy

- Strategy: MVP-first | Incremental | Parallel-team
- Reason:

## Task Contract

Each task must include an ID, target, linked `REQ-*`/`AC-*`, action, and proof. Use `[P]` only for genuinely independent work. For story phases, include `[US1]`, `[US2]`, and so on after the optional `[P]` marker. Tasks are the single executable checklist and source of machine-controlled status.

## Tasks

Group every `T-NNN` under this heading. Milestone subsections below remain procedure guidance; `## Tasks` is the runtime-checked heading.

## Phase 1: Setup / Foundational — <name>

- Goal:
- Entry proof:
- Exit proof:

- [ ] T-001 [P?] [US1?] Target — action
  - Covers: `AC-001`
  - Depends on:
  - Proof: exact command/observation
  - Evidence:

## Phase 2: User Story 1 — <name> (Priority: P1) 🎯 MVP

- Goal:
- Entry proof:
- Exit proof:

- [ ] T-002 [P?] [US2?] Target — action
  - Covers: `AC-002`
  - Depends on: `T-001`
  - Proof: exact command/observation
  - Evidence:

## Resume Notes

- Next recommended task:

Rules:
- Group every task under exactly one ordered milestone.
- Order milestones top-to-bottom by implementation sequence.
- Keep `T-NNN` checkboxes as the only task state; do not add separate milestone checkboxes.
- A milestone is complete when all child tasks are `Done` and its exit proof passes.
- Keep each task independently executable and mark it done only with evidence.
- Prefer **tracer bullets**: each task is a narrow complete path through every layer it touches, demoable or verifiable on its own.
- Wide mechanical refactors use **expand → migrate in batches → contract**, each step a `T-NNN` with proof.
- Architecture-shaping tasks must target paths from the plan module map and preserve its ownership/dependency boundaries.
- Simple features use one compact milestone with only applicable fields.
