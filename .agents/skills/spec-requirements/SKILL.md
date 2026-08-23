---
id: skill-spec-requirements
name: spec-requirements
description: "Define the 'What & Why' of a feature. Handles specification authoring, Socratic refinement to resolve ambiguity, and a built-in readiness review to ensure requirements are testable and complete before planning."
tags: ['spec', 'requirements', 'analysis']
triggers: ['requirement', 'spec', 'feature']
---
# Spec Requirements

## At a Glance

| | |
|---|---|
| **Reads** | `product-sense.md`, `project-constraints.md`, optional `analysis.md` |
| **Writes** | Required: `spec.md`. Optional: `proposal.md`, `requirements-review.md`, `status.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-requirements --feature <slug> --intent "<request>"`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-requirements --feature <slug> --handoff spec-plan` |
| **Entry** | Direct peer skill; handoff may suggest `/spec-plan` |

## Overview

Author `spec.md` with `REQ-*`, binary `AC-*`, `US-*`, and `SC-*`. What/why only — no implementation leakage.

## When to Use & Invocation Triggers

- **When to Use**: new feature; refine spec/ACs; resolve ambiguity; re-grill mid-plan/implement questions.
- **Triggers**: `requirement`, `spec`, `feature`

## Execution Modes & Profiles

| Mode | Condition | Output |
|---|---|---|
| `full-intake` | No `spec.md` | Alignment, grilling, profile, proposal, `spec.md` |
| `clarify-reentry` | Spec exists with open questions or `[:HALT ...]` | Patch spec; stamp `[:HALT STALE]` if plan exists |

## I/O & Artifact Protocol

- **Reads**: `analysis.md` if present, `status.md`, `product-sense.md`, `project-constraints.md`, `adr-log.md`.
- **Writes**: `spec.md`; `status.md` (`Specifying` → `SpecApproved`); `proposal.md` (Moderate/Complex); optional `requirements-review.md`.
- **Session**: `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-requirements --feature <slug> --intent "<request>"`.
   - Omit `--full` unless compacted, new chat on existing feature, reload requested, or pack stale. See `skills/_shared/context-loading.md`.
   - Do not hand-edit `- Phase:`. Envelope creates `status.md` and sets `Specifying`.

2. **Intake**:
   - Classify input (`new_spec`, `spec_slice`, `change_request`, `new_initiative`, `maintenance`, `harness_improvement`) per `references/intake.md`.
   - Pass request as `--intent`. Domain packs match `triggers:` in `corebase-specharness/memories/domain/<name>/glossary.md`.
   - Read `analysis.md` if present.
   - If spec contradicts a locked ADR, write `[:HALT ADR CONFLICT: ADR-NNN]` and block handoff.

3. **Clarification**:
   - Calibrate familiarity (Novice/Familiar/Expert) and urgency (Relaxed/Normal/Urgent).
   - Frontier grilling per `references/grilling-waves.md`: all unblocked questions in numbered batches with recommended defaults.
   - Discover repo facts by inspection; ask only domain, trade-off, and scope decisions.
   - Capture resolved terms into `glossary.md` immediately.
   - Contradictory after 2 rounds → `[:HALT UNRESOLVED]`.

4. **Profile & proposal**:
   - Classify `Simple` / `Moderate` / `Complex` in `status.md`.
   - Draft `proposal.md` via `references/proposal-template.md` (skip for `Simple`).

5. **Author `spec.md`**:
   - Use `references/spec-template.md`. Define `REQ-*` and binary `AC-*`.
   - Moderate/Complex: prioritize `US1`/P1 MVP, `US2`/P2, …
   - Bind every NFR to ≥1 `AC-*` via `Linked ACs:`.
   - Every `AC-*` needs an observable assertion and verification mechanism.

6. **Review & handoff**:
   - Zero HALT tags remaining.
   - Readiness review per `references/requirements-review-template.md`. Write `requirements-review.md` only if gaps exist.
   - `python3 corebase-specharness/scripts/core/cli.py phase-check --feature <slug> --skill spec-requirements`.
   - Mark `Spec approved` `[x]`, then `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-requirements --feature <slug> --handoff spec-plan`.
   - Public API/CLI/schema docs may use an external skill; not a CoreBase route.

## Anti-Patterns & Red Flags

- Vague ACs ("fast", "working") instead of binary assertions.
- NFRs with no `AC-*` binding.
- Implementation leakage ("use Redis") in the spec.
- Adding unrequested requirements without confirmation.

## Core Rules

- Never invent business logic; grill or mark `[:HALT UNRESOLVED]`.
- Every AC MUST be binary and provable.
- Every NFR MUST reference ≥1 AC.
- What/why only. How belongs in the plan.
