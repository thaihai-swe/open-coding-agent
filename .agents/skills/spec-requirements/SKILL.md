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
| **Reads** | `core-zero/project/product-sense.md`, `core-zero/project/project-constraints.md`, optional `analysis.md` |
| **Writes** | Required: `spec.md`. Optional: `proposal.md`, `requirements-review.md`, `status.md` |
| **Key CLI** | `python3 core-zero/scripts/core/cli.py skill-enter --skill spec-requirements --feature <slug> --intent "<request>"`, `python3 core-zero/scripts/core/cli.py skill-exit --skill spec-requirements --feature <slug> --handoff spec-plan` |
| **Entry** | Directly invokable peer skill; handoff may suggest `/spec-plan` |

## Overview

Create or refine `status.md`, `proposal.md`, `spec.md`, and (if issues are found) `requirements-review.md` in `artifacts/features/<slug>/`. This skill aligns the team on what is being built and how it will be verified.

Defines functional requirements (`REQ-*`), testable acceptance criteria (`AC-*`), user stories (`US-*`), and success criteria (`SC-*`) without leaking implementation details.

## When to Use & Invocation Triggers

- **When to Use**:
  - Defining a new feature, change request, or initiative.
  - Refining existing specifications or acceptance criteria.
  - Resolving ambiguity before technical planning.
  - *Clarify Re-Entry*: Re-grilling open questions when mid-plan or mid-implement scope questions arise.
- **Triggers**: `requirement`, `spec`, `feature`

## Execution Modes & Profiles

| Mode | Condition / Trigger | Primary Purpose & Outputs |
|---|---|---|
| `full-intake` | No `spec.md` exists, or creating a new feature from scratch | Complete 9-step intake: alignment, Socratic grilling, delivery profile, proposal, `spec.md` authoring |
| `clarify-reentry` | Non-empty `spec.md` exists, but open questions or `[:HALT ...]` remain | Targeted update: loads existing spec, grills unresolved questions, patches `spec.md`, stamps `[:HALT STALE]` if plan exists |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/analysis.md` (if present), `artifacts/features/<slug>/status.md`, `core-zero/project/product-sense.md`, `core-zero/project/project-constraints.md`, `core-zero/memories/repo/adr-log.md`.
- **Writes**:
  - `artifacts/features/<slug>/spec.md` (`REQ-*`, `AC-*`, `SC-*`)
  - `artifacts/features/<slug>/status.md` via `skill-enter` (`Specifying`) and `skill-exit` (`SpecApproved`)
  - `artifacts/features/<slug>/proposal.md` (Moderate and Complex profiles)
  - Optional `artifacts/features/<slug>/requirements-review.md` (if readiness review flags issues)
- **Session State**: Updates `.corezero/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 core-zero/scripts/core/cli.py skill-enter --skill spec-requirements --feature <slug> --intent "<request>"`.
   - Do not hand-edit `- Phase:`. The envelope creates `status.md` if needed and sets `Specifying`.

2. **Intake & Context Alignment**:
   - Classify input type (`new_spec`, `spec_slice`, `change_request`, `new_initiative`, `maintenance`) in `status.md` per `references/intake.md`.
   - Supply the feature request as `--intent` to context loading. CoreZero discovers nested domain packs by matching that intent against `triggers:` in `core-zero/memories/domain/<name>/glossary.md`.
   - Read research findings in `analysis.md` if available.
   - Check `core-zero/memories/repo/adr-log.md`. If proposed spec contradicts a locked ADR, write `[:HALT ADR CONFLICT: ADR-NNN]` and block handoff.

3. **Clarification Phase (Frontier Grilling)**:
   - Calibrate user domain familiarity (Novice / Familiar / Expert) and urgency (Relaxed / Normal / Urgent).
   - Execute wave-based grilling per `references/grilling-waves.md` using the **frontier-round protocol**. Ask all unblocked questions together in numbered batches with recommended defaults.
   - Separate facts from decisions: discover repository facts through codebase inspection or subagents; ask the user only for domain, trade-off, and scope decisions.
   - Capture resolved domain terms into `core-zero/project/glossary.md` (or domain pack) immediately as they crystallize.
   - If answers remain contradictory after 2 rounds, write `[:HALT UNRESOLVED]` and escalate.

4. **Profile Classification & Proposal**:
   - Classify scope into `Simple`, `Moderate`, or `Complex` and write to `status.md`.
   - Draft `proposal.md` using `references/proposal-template.md` (skip for `Simple`).

5. **Spec Authoring (`spec.md`)**:
   - Author `spec.md` using `references/spec-template.md`.
   - Define `REQ-*` functional requirements and `AC-*` binary acceptance criteria.
   - For `Moderate`/`Complex`: Organize requirements into prioritized user stories (`US1`/P1 MVP, `US2`/P2, etc.).
   - Link every Non-Functional Requirement (NFR) to at least one `AC-*` via `Linked ACs:`.
   - Ensure every `AC-*` specifies an observable assertion and a verification mechanism.

6. **Completeness Review & Phase Gate Handoff**:
   - Verify zero HALT tags (`[:HALT NEEDS CLARIFICATION]`, `[:HALT UNRESOLVED]`, `[:HALT ADR CONFLICT]`) remain.
   - Conduct readiness review per `references/requirements-review-template.md`. Create `requirements-review.md` only if gaps are found.
   - Run `python3 core-zero/scripts/core/cli.py phase-check --feature <slug> --skill spec-requirements`.
   - Mark `Spec approved` `[x]`, then run `python3 core-zero/scripts/core/cli.py skill-exit --skill spec-requirements --feature <slug> --handoff spec-plan`.
   - If acceptance criteria define a public API, CLI, or schema, an adopter may use a separately installed external documentation skill; CoreZero does not route or require it.

## Anti-Patterns & Red Flags

- **Ambiguous Acceptance Criteria**: Writing "the system should be fast/working" instead of binary pass/fail assertions.
- **Isolated NFRs**: Listing performance or security constraints without binding them to an `AC-*`.
- **Implementation Leakage**: Specifying code/framework choices ("use Redis for cache") in the spec — What/Why belongs in spec, How belongs in plan.
- **Silent Scope Creep**: Adding unrequested requirements during grilling without user confirmation.

## Core Rules

- **Anti-Hallucination**: Never invent unspecified business logic; resolve ambiguities through grilling or mark `[:HALT UNRESOLVED]`.
- **Deterministic ACs**: Every acceptance criterion MUST be binary and provable.
- **NFR-AC Binding**: Every non-functional requirement MUST reference at least one acceptance criterion.
- **What, Not How**: Focus exclusively on problem domain and acceptance criteria, avoiding technical design leakage.
