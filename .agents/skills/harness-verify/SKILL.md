---
id: skill-harness-verify
name: harness-verify
description: "Verify implemented work against the spec and plan. Handles split verification modes, mechanical gates, optional fallow-pass cleanup, manual testing guides, and final closeout authority."
tags: ['harness', 'verification', 'gates']
triggers: ['verify', 'gate', 'test', 'validation']
---
# Harness Verify

## At a Glance

| | |
|---|---|
| **Reads** | `corebase-specharness/rules/security.md` (§Verification), `corebase-specharness/project/harness-config.yaml`, `spec.md`, `tasks.md`, `plan.md` |
| **Writes** | Required: `review.md`. Optional: `status.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill harness-verify --feature <slug>`, `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill harness-verify`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill harness-verify --feature <slug> --handoff context-memory` |
| **Suggested Handoff** | `/context-memory` (after `Done`; Post-Ship Sync heading is required first) |

## Overview

Closes the loop on a feature. Updates `status.md` to `Verifying`, runs mechanical gate runners, audits AC-to-task traceability, performs security policy audits, and writes the final verdict in `artifacts/features/<slug>/review.md`.

This skill is the **sole authority** for validating AC completion and transitioning a feature state to `Done`.

## When to Use & Invocation Triggers

- **When to Use**:
  - After all implementation tasks in `tasks.md` are completed.
  - Re-evaluating feature verification after a fix or replan.
- **Triggers**: `verify`, `gate`, `test`, `validation`

## Execution Modes & Profiles

| Verification Pass | Scope & Purpose | Required Outputs / Tables |
|---|---|---|
| `mechanical-gate` | Runs configured build, lint, and test runners in `harness-config.yaml` | Recorded pass/fail outcomes in `review.md` and diagnostic evidence |
| `alignment-audit` | Audits bidirectional AC-to-task-to-proof traceability | `AC-ID \| Task-ID \| Proof Evidence \| Pass/Fail` table |
| `design-conformance` | Verifies delivered code against `plan.md` technical design | `Design Element \| Evidence Location \| Pass/Fail` table |
| `security-audit` | Audits scope against `core-policies.md` `## Security Policy` | Security Audit section in `review.md` |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/spec.md`, `artifacts/features/<slug>/plan.md`, `artifacts/features/<slug>/tasks.md`, `corebase-specharness/project/harness-config.yaml`, `corebase-specharness/rules/security.md`.
- **Writes**:
  - `artifacts/features/<slug>/review.md` (verdict, gate outcomes, traceability tables)
  - `artifacts/features/<slug>/status.md` via `skill-enter` (`Verifying`) and `skill-exit` (`Done` or `--phase ChangesRequested`)
- **Session State**: Updates `.corebase-specharness/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill harness-verify --feature <slug> --intent "<request>"`.
   - Omit `--full` unless this conversation was compacted, this is the first skill in a new chat on an existing feature, the user asked to reload context, or the pack is known stale. See `skills/_shared/context-loading.md`.
   - Run `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill harness-verify`.

2. **Mechanical Gate Audit**:
   - Run `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug> --skill harness-verify` to mechanically execute all confirmed project gates.
   - Run `python3 corebase-specharness/scripts/core/cli.py artifact-check --feature <slug> --skill harness-verify --trace` to verify artifact structure and AC traceability.

3. **Alignment, Two-Axis Review & Conformance Audit**:
   - *Traceability Check*: Map every `AC-*` in `spec.md` to a completed `T-NNN` task in `tasks.md` with fresh proof evidence. Zero tolerance — unmapped AC = `Fail`.
   - *Two-Axis Isolated Review*: After mechanical `verify`, review the `git` diff independently on two axes. Run them as isolated parallel subagents when the runtime provides them; otherwise run sequentially without mixing findings:
     1. **Standards**: audit against `code-design.md`, `security.md`, `ponytail.md`, plus the Fowler smell baseline in `references/review-template.md`. Repo rules override the baseline. Baseline smells are judgement calls, never hard violations. Skip anything tooling already enforces.
     2. **Spec**: audit the implemented behavior against `spec.md` for missing/partial `AC-*`, unrequested behavior, and implementations that look implemented but are wrong. Cite the spec line for each finding.
     Present both reports side by side. Do not merge or rerank findings across axes.
   - *Design Conformance*: Verify delivered architecture against `plan.md`.
   - *Dropped Behavior Check*: Inspect `git diff` for deleted public surface or removed tests without spec justification.

4. **Security & Review Provider Audits**:
   - Audit against `core-policies.md` `## Security Policy`.
   - Record the review-provider outcome from `verify` in `review.md` `## Provider Review`. The kit default is `providers.review.active: none` and `mode: optional`: no `ocr` binary is required, and a missing provider is `deferred`, not a Fail. Two-axis review above is the required review. Enable `open-code-review` in `corebase-specharness/project/tool-providers.md` only after local `ocr` setup. Set `mode: required` only when this project must fail closeout without a successful `ocr review`.

5. **Memory Sync Trigger & Final Closeout**:
   - When all verification evidence passes, record `Verification passed; sync pending`.
   - Write `## Post-Ship Sync` in `session-extracts.md` (use `no candidates` when none exist). `skill-exit` to `Done` fails without that heading and without `review.md`.
   - Invoke `/context-memory` after `Done` to promote candidate lessons. If the heading is skipped, insert `[:HALT SYNC REQUIRED]` and do not exit to `Done`.
   - Write verdict (`Pass`, `Pass with Follow-Up Debt`, or `Fail`) in `artifacts/features/<slug>/review.md` using `references/review-template.md`.
   - On a passing verdict, confirm `verify` reports `details.verified: true`; then run `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill harness-verify --feature <slug> --handoff context-memory` (which performs inline mechanical verification).
    - If no confirmed gates exist or verification is not true, do not close normally. Use `ChangesRequested`, configure gates, or record a deliberate `--verification-override --override-reason "..."` exception.
   - On a failing verdict run `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill harness-verify --feature <slug> --phase ChangesRequested --handoff spec-implement`.

## Anti-Patterns & Red Flags

- **Premature Done**: Setting phase to `Done` without running mechanical verification or post-ship memory sync.
- **Unmapped ACs**: Passing verification when an `AC-*` item has zero task proof evidence.
- **Stale Verification**: Accepting test logs from prior sessions instead of fresh terminal execution.
- **Ignoring Gate Failures**: Glossing over broken build/test output from `python3 corebase-specharness/scripts/core/cli.py verify`.

## Core Rules

- **Sole Done Authority**: This skill is the ONLY skill authorized to `skill-exit` with phase `Done`.
- **Zero-Tolerance Alignment**: Every `AC-*` MUST map to at least one task with verifiable proof.
- **Mandatory Memory Sync**: Write `## Post-Ship Sync` before `skill-exit` to `Done`, then hand off to `/context-memory` for promotion.
- **Proof Must Match Plan**: Require verification on the planned proof surfaces.
