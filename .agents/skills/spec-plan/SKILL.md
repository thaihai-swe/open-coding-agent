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
| **Reads** | `architecture.md`, `ponytail.md`, `code-design.md`, `spec.md`, `status.md` |
| **Writes** | Required: `plan.md`. Optional: `status.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-plan --feature <slug> --intent "<request>"`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-plan --feature <slug> --handoff spec-tasks` |
| **Entry** | Direct peer skill; handoff may suggest `/spec-tasks` |

## Overview

Turn approved `spec.md` into `plan.md`: module map, seams, dependency direction, complexity tracking, proof strategy. `/spec-tasks` derives the graph from this design.

## When to Use & Invocation Triggers

- **When to Use**: technical design for approved spec; component mapping; re-plan after a structural flaw.
- **Triggers**: `plan`, `design`, `architecture`, `technical design`

## Execution Modes & Profiles

| Mode | Profile | Depth |
|---|---|---|
| `simple-plan` | `Simple` | Metadata, lightweight design, basic proof |
| `moderate-plan` | `Moderate` | Full design, module map, risk mitigation |
| `complex-plan` | `Complex` | Full design + complexity tracking; halt to `/spec-research` if risk unverified |

## I/O & Artifact Protocol

- **Reads**: `spec.md`, `status.md`, `architecture.md`, `code-design.md`, `ponytail.md`.
- **Writes**: `plan.md`; `status.md` (`Planning`).
- **Session**: `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-plan --feature <slug> --intent "<request>"`.
   - Omit `--full` unless compacted, new chat on existing feature, reload requested, or pack stale. See `skills/_shared/context-loading.md`.
   - Do not hand-edit `- Phase:`.

2. **Author**:
   - Write `plan.md` via `references/plan-template.md`.
   - Apply `code-design.md`, `ponytail.md`, `references/deep-modules.md`.
   - Match depth to `Simple` / `Moderate` / `Complex`.

3. **Module map & seams**:
   - Every file path, public seam, single responsibility, dependency direction, split/co-location rationale.
   - Deletion test on every new module. Collapse shallow pass-throughs.
   - Co-locate collaborators that change together; split independent responsibilities and UI/domain/infra.

4. **Complexity & decisions**:
   - Record Ponytail exceptions in `## Complexity Tracking`.
   - Complex, or Moderate with two viable interfaces: Design-it-Twice. Record rejected option in `## Alternatives Considered`.
   - Material trade-offs → `/spec-adr`. Design-it-twice is not an ADR.

5. **Handoff**:
   - Optional diagrams/docs via `EXTERNAL_SKILLS.md` do not change lifecycle ownership.
   - `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-plan --feature <slug> --handoff spec-tasks`.
   - Do NOT pass `--phase PlanApproved`; `/spec-tasks` owns that after the graph exists.

## Anti-Patterns & Red Flags

- Unrelated responsibilities in one file without rationale.
- Tasks or code before design is done.
- Choosing libraries/patterns without an ADR.
- Abstractions or caches beyond `spec.md`.

## Core Rules

- Design only for approved requirements.
- Use language/framework features directly; avoid custom wrappers.
- If `spec.md` changes, stamp `[:HALT STALE — spec amended <date>]` and re-plan.
- Cite applied `LH-*` heuristics.
