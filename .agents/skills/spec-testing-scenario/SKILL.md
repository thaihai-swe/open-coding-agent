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
| **Entry** | Direct peer skill; return to caller after the bounded procedure |

## Overview

Produce `testing-scenarios.md`: executable manual cases for happy paths, edges, failures, and sign-off. Optional and non-blocking.

## When to Use & Invocation Triggers

- **When to Use**: after `/spec-plan` (clarify QA); after `/spec-implement` (execution sheets); anytime manual docs add value.
- **Triggers**: `testing scenario`, `test scenarios`, `test guide`, `manual test`, `testing-scenarios`

## Execution Modes & Profiles

| Mode | Focus | Output |
|---|---|---|
| `happy-path` | Core functional | End-to-end workflows per `AC-*` |
| `edge-case` | Boundary & error | Equivalence, boundary, race, idempotency, security |
| `full-suite` | Release sheet | Happy + edge + regression + sign-off |

## I/O & Artifact Protocol

- **Reads**: `spec.md` (`AC-*`), `plan.md`, `tasks.md` when present.
- **Writes**: `testing-scenarios.md`.
- **Session**: note generation in `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Identify `<slug>`. Extract every `AC-*`. Read `plan.md` and `tasks.md` for scope.

2. **Edge-case discovery**:
   - For each `AC-*`, identify the public seam (`skills/spec-implement/references/tdd-loop.md`).
   - Test through the public seam; never against private state.
   - Heuristics: equivalence/boundary (min, max, empty, max+1); state/error injection; auth (unauth, expiry, SQLi/XSS); idempotency and concurrency.

3. **Author**:
   - Write `testing-scenarios.md` via `references/testing-scenarios-template.md`.
   - Precondition data, numbered steps, expected result per case.
   - Leave `Actual result`, `Status`, `Tester/date` blank.

4. **Review & return**:
   - Every `AC-*` has ≥1 scenario. Mark ambiguous expected results `[CLARIFY]`.
   - Return to caller (`/spec-implement` or `/harness-verify`).

## Anti-Patterns & Red Flags

- Scenarios that do not trace to an `AC-*`.
- Vague steps ("test the button") instead of numbered steps and data.
- Happy-path only; missing boundary, error, and security cases.

## Core Rules

- Every `AC-*` MUST map to ≥1 test case.
- Observe the same public seam as implementation proofs.
- Mark ambiguous outcomes `[CLARIFY]`; do not invent business logic.
- Never blocks lifecycle progression.
