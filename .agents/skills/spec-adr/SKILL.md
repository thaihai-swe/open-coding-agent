---
id: skill-spec-adr
name: spec-adr
description: "Create or evaluate an Architecture Decision Record (ADR). Ensures structural choices, technology selections, and major design trade-offs are documented with rationale and long-term consequences."
tags: ['spec', 'decision', 'architecture']
triggers: ['adr', 'decision', 'architecture decision']
---
# Spec ADR

## At a Glance

| | |
|---|---|
| **Reads** | Codebase, `ponytail.md`, `architecture.md`, `spec.md`, `plan.md` |
| **Writes** | Optional: `corebase-specharness/project/adr/`, `corebase-specharness/memories/repo/adr-log.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py adr-generate --title "<title>"`, `python3 corebase-specharness/scripts/core/cli.py context-load --skill spec-adr` |
| **Entry** | Direct peer skill; return to caller after the bounded procedure |

## Overview

Create, update, or evaluate ADRs. Evaluates structural patterns and technology choices against alternatives, documents rationale, and appends to `adr-log.md`.

## When to Use & Invocation Triggers

- **When to Use**: technology/library choices; structural trade-offs / major refactors; contested design options.
- **Triggers**: `adr`, `decision`, `architecture decision`

## Execution Modes & Profiles

| Mode | Trigger | Output |
|---|---|---|
| `adr-major` | High-impact architectural / tech choice | Full ADR in `corebase-specharness/project/adr/` |
| `adr-lightweight` | Minor choice or localized trade-off | Lightweight ADR |
| `adr-review` | Evaluate ADR or check conflicts | Assess status (`Proposed`/`Accepted`/`Deprecated`/`Superseded`) |

## I/O & Artifact Protocol

- **Reads**: `architecture.md`, `ponytail.md`, `spec.md`, `plan.md`.
- **Writes**: `corebase-specharness/project/adr/[number]-[slug].md`; `corebase-specharness/memories/repo/adr-log.md`.
- **Session**: note decision in `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Confirm trade-offs exist between ≥2 viable options.

2. **Comparative Evaluation**:
   - Compare ≥2 options across complexity, maintenance, performance, familiarity.
   - Apply `ponytail.md` (native > stdlib > installed > custom) and `references/deep-modules.md`.
   - Deletion test + Design-it-Twice: compare interface depth, seam placement, blast radius, test surface.
   - Classify reversibility (`Easy | Moderate | Hard`). Prefer easy-to-reverse options under uncertainty.

3. **Draft ADR**:
   - `python3 corebase-specharness/scripts/core/cli.py adr-generate --title "<title>"` or create `corebase-specharness/project/adr/[number]-[slug].md`.
   - Problem statement, options pros/cons, decision, consequences via `references/adr-template.md`.

4. **Log Ledger**:
   - Append to `corebase-specharness/memories/repo/adr-log.md` conforming to `## Entry Template`.
   - Status: `Proposed` or `Accepted`. Link to `spec.md` or `plan.md`.

5. **Return**:
   - Return to calling skill (`/spec-plan`, `/spec-requirements`, `/spec-implement`).

## Anti-Patterns & Red Flags

- Single-option ADR without alternatives.
- Major component changes without an ADR.
- Editing past accepted ADRs instead of marking `Superseded`.

## Core Rules

- Sole skill authorized to append to `adr-log.md`.
- Every ADR MUST evaluate ≥2 options with depth, seam, blast radius, and reversibility.
- Accepted ADR entries are immutable. Superseded decisions MUST create a new ADR.
- Design-it-Twice in `plan.md` does not replace an ADR for hard-to-reverse choices.
