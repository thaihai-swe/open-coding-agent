---
id: skill-spec-testing-scenario
name: spec-testing-scenario
description: "Draft an executable manual test-case guide for a feature. Fully optional and user-invoked — use it when QC or manual testers need repeatable test cases before or after implementation."
tags: ['spec', 'testing', 'scenarios', 'manual-testing']
triggers: ['testing scenario', 'test scenarios', 'test guide', 'manual test', 'testing-scenarios']
---
# Spec Testing Scenario

## At a Glance

| | |
|---|---|
| **Reads** | `artifacts/features/<slug>/spec.md`, `plan.md`, `tasks.md` |
| **Writes** | Required: `testing-scenarios.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-testing-scenario` |
| **Entry** | Directly invokable peer skill; return to the caller after the bounded procedure |

## Overview

Produces `artifacts/features/<slug>/testing-scenarios.md` — an executable, human-readable manual test-case guide covering happy paths, edge cases, failure paths, and sign-off criteria.

Provides QC and manual testers with setup steps, test data, expected results, and execution recording fields. Fully optional and non-blocking.

## When to Use & Invocation Triggers

- **When to Use**:
  - After `/spec-plan` (before implementation, to clarify manual QA expectations).
  - After `/spec-implement` (to produce execution test sheets for delivered features).
  - Standalone whenever manual test documentation adds team value.
- **Triggers**: `testing scenario`, `test scenarios`, `test guide`, `manual test`, `testing-scenarios`

## Execution Modes & Profiles

| Mode | Focus | Target Scenarios & Output |
|---|---|---|
| `happy-path` | Core functional validation | Maps direct end-to-end user workflows for each `AC-*` |
| `edge-case` | Boundary & error injection | Systematic edge-case discovery (equivalence, boundary, race, idempotency, security) |
| `full-suite` | Complete QA release sheet | Combines happy-path, edge-case, and regression checks with sign-off tables |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/spec.md` (`AC-*`), `artifacts/features/<slug>/plan.md`, `artifacts/features/<slug>/tasks.md` (when available).
- **Writes**: `artifacts/features/<slug>/testing-scenarios.md`.
- **Session State**: Notes test sheet generation in `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight & Input Gathering**:
   - Identify `<slug>`. Read `spec.md` to extract all `AC-*` items. Read `plan.md` and `tasks.md` for implementation scope.

2. **Systematic Edge-Case Discovery**:
   - For each `AC-*`, identify the public seam where behavior is observed, following `skills/spec-implement/references/tdd-loop.md`.
   - Test through the public seam; do not write manual scenarios against private implementation state.
   - Apply edge-case heuristics:
     - Equivalence partitioning & Boundary-value analysis (min, max, empty, max+1).
     - State-transition & Error-injection (timeouts, API errors, DB drops).
     - Security/auth (unauthenticated access, token expiry, SQLi/XSS).
     - Idempotency & Concurrency (double submits, parallel triggers).

3. **Scenario Authoring**:
   - Author `artifacts/features/<slug>/testing-scenarios.md` using `references/testing-scenarios-template.md`.
   - Provide precondition data, numbered tester steps, and expected result for every test case.
   - Leave `Actual result`, `Status`, and `Tester/date` blank for QA execution.

4. **Review & Return**:
   - Verify every `AC-*` has at least one scenario. Mark ambiguous expected results as `[CLARIFY]`.
   - Return control to calling skill (`/spec-implement` or `/harness-verify`).

## Anti-Patterns & Red Flags

- **Orphan Acceptance Criteria**: Creating test scenarios that do not trace back to an `AC-*`.
- **Non-Runnable Steps**: Writing vague instructions ("test the button") instead of explicit numbered steps and test data.
- **Happy-Path Tunnel Vision**: Omitting boundary values, error injection, and security cases.

## Core Rules

- **AC Traceability**: Every `AC-*` in `spec.md` MUST map to at least one test case.
- **Public Seam Only**: Steps and expected results observe the same public seam used by implementation proofs. Do not require private-state inspection.
- **No Invented Outcomes**: Mark ambiguous expected outcomes as `[CLARIFY]` instead of fabricating business logic.
- **Non-Gating Optionality**: This skill produces documentation and NEVER blocks lifecycle phase progression.
