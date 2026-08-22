---
id: skill-spec-plan
name: spec-plan
description: "Design the technical solution and module map from an approved spec. Defines component boundaries, data flow, complexity tracking, and proof strategies before task breakdown."
tags: ['spec', 'planning', 'design']
triggers: ['plan', 'design', 'architecture', 'technical design']
---
# Spec Plan

## At a Glance

| | |
|---|---|
| **Reads** | `core-zero/project/architecture.md`, `core-zero/rules/ponytail.md`, `core-zero/rules/code-design.md`, `spec.md`, `status.md` |
| **Writes** | Required: `plan.md`. Optional: `status.md` |
| **Key CLI** | `python3 core-zero/scripts/core/cli.py skill-enter --skill spec-plan --feature <slug> --intent "<request>"`, `python3 core-zero/scripts/core/cli.py skill-exit --skill spec-plan --feature <slug> --handoff spec-tasks` |
| **Entry** | Directly invokable peer skill; handoff may suggest `/spec-tasks` |

## Overview

Converts an approved spec into a safe, concrete technical design in `artifacts/features/<slug>/plan.md`. It answers: how will we build this safely? 

Defines module maps, component boundaries, dependency directions, complexity tracking, and proof strategies. `/spec-tasks` subsequently derives the executable task graph from this technical design.

## When to Use & Invocation Triggers

- **When to Use**:
  - Technical solution design for an approved `spec.md`.
  - Architecture and component mapping before breaking work into tasks.
  - Re-planning when implementation reveals a structural design flaw.
- **Triggers**: `plan`, `design`, `architecture`, `technical design`

## Execution Modes & Profiles

| Mode / Profile | Scope Condition | Required Design Depth |
|---|---|---|
| `simple-plan` | Delivery profile `Simple` | Compact `plan.md` with Metadata, Lightweight Design, and basic proof strategy |
| `moderate-plan` | Delivery profile `Moderate` | Comprehensive design, explicit module map, and risk mitigation |
| `complex-plan` | Delivery profile `Complex` | Comprehensive design, module map, explicit complexity tracking; halt to `/spec-research` if technical risk is unverified |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/spec.md`, `artifacts/features/<slug>/status.md`, `core-zero/project/architecture.md`, `core-zero/rules/code-design.md`, `core-zero/rules/ponytail.md`.
- **Writes**:
  - `artifacts/features/<slug>/plan.md`
  - `artifacts/features/<slug>/status.md` via `skill-enter` / `skill-exit` (`Planning`)
- **Session State**: Updates `.corezero/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 core-zero/scripts/core/cli.py skill-enter --skill spec-plan --feature <slug> --intent "<request>"`.
   - Do not hand-edit `- Phase:`.

2. **Technical Solution Authoring**:
   - Author `artifacts/features/<slug>/plan.md` using `references/plan-template.md`.
   - Apply `core-zero/rules/code-design.md`, `core-zero/rules/ponytail.md`, and `references/deep-modules.md`.
   - Tailor design depth based on delivery profile (`Simple`, `Moderate`, or `Complex`).

3. **Module Map & Seam Definition**:
   - Write explicit module map: specify every file path, public interface/seam, single responsibility, dependency direction, and split/co-location rationale.
   - Apply the deletion test to every proposed new module or wrapper. Collapse shallow pass-throughs.
   - Co-locate collaborators that change together; split independently changing responsibilities, UI/domain/infra boundaries, or distinct side effects.

4. **Complexity, Design-it-Twice & Decision Gates**:
   - *Complexity Gate*: Record deliberate exceptions to the Ponytail simplicity ladder in `## Complexity Tracking`. Justify why native/standard library options are insufficient.
   - *Design-it-Twice*: For Complex features, and for Moderate features with two viable interface shapes, sketch two alternative interfaces. Compare them on depth, seam placement, and blast radius. Record the rejected option in `## Alternatives Considered`.
   - *Decision Gate*: If two viable technical options have material trade-offs, invoke `/spec-adr` — do not choose silently. Design-it-twice does not replace an ADR.

5. **External Specialist Alignment & Handoff**:
   - Optional design analysis, diagrams, and technical documentation may be created with separately installed skills described in `EXTERNAL_SKILLS.md`. They are outside CoreZero routing and do not change lifecycle ownership.
   - Run `python3 core-zero/scripts/core/cli.py skill-exit --skill spec-plan --feature <slug> --handoff spec-tasks`.
   - Do NOT pass `--phase PlanApproved`; that state is owned by `/spec-tasks` after the task graph is created.

## Anti-Patterns & Red Flags

- **Monolithic Bundling**: Grouping unrelated responsibilities into a single file without co-location rationale.
- **Design After Tasks**: Defining tasks or coding before completing technical design.
- **Undocumented Trade-Offs**: Choosing between competing libraries or architectural patterns without an ADR.
- **Premature Optimization**: Designing abstractions or caching layers beyond what `spec.md` requested.

## Core Rules

- **Simplicity Gate**: No speculative future-proofing — design only for approved requirements.
- **Anti-Abstraction Gate**: Use framework and language features directly; avoid custom wrappers.
- **Spec Immutability**: Stick to approved requirements. If `spec.md` changes, stamp `[:HALT STALE — spec amended <date>]` on plan/tasks and re-plan.
- **Cite Heuristics**: Cite relevant `LH-*` heuristics applied in design rationale.
