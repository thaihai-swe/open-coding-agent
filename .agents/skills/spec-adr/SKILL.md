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
| **Reads** | Codebase context, `core-zero/rules/ponytail.md`, `core-zero/project/architecture.md`, `spec.md`, `plan.md` |
| **Writes** | Optional: `core-zero/project/adr/`, `core-zero/memories/repo/adr-log.md` |
| **Key CLI** | `python3 core-zero/scripts/core/cli.py adr-generate --title "<title>"`, `python3 core-zero/scripts/core/cli.py context-load --skill spec-adr` |
| **Entry** | Directly invokable peer skill; return to the caller after the bounded procedure |

## Overview

Creates, updates, or evaluates Architecture Decision Records (ADRs). Ensures that technology choices, structural patterns, and design trade-offs are evaluated against alternatives, documented with rationale, and indexed in the repository ledger (`adr-log.md`).

Can be invoked conditionally from `/spec-requirements`, `/spec-plan`, `/spec-tasks`, or `/spec-implement`.

## When to Use & Invocation Triggers

- **When to Use**:
  - Selecting technologies or libraries (e.g., Kafka vs SQS, PostgreSQL vs DynamoDB).
  - Documenting structural trade-offs or architectural refactoring decisions.
  - Resolving contested design choices when two viable options emerge.
- **Triggers**: `adr`, `decision`, `architecture decision`

## Execution Modes & Profiles

| Mode | Trigger / Condition | Primary Purpose & Outputs |
|---|---|---|
| `adr-major` | High-impact architectural or technology choice | Creates full ADR in `core-zero/project/adr/` using `references/adr-template.md` |
| `adr-lightweight` | Minor design choice or localized trade-off | Creates lightweight ADR using `references/adr-lightweight-template.md` |
| `adr-review` | Evaluating an existing ADR or checking for conflicts | Assesses current ADR status (`Proposed`, `Accepted`, `Deprecated`, `Superseded`) |

## I/O & Artifact Protocol

- **Reads**: `core-zero/project/architecture.md`, `core-zero/rules/ponytail.md`, `artifacts/features/<slug>/spec.md`, `artifacts/features/<slug>/plan.md` (when present).
- **Writes**:
  - `core-zero/project/adr/[number]-[slug].md` (new ADR document)
  - `core-zero/memories/repo/adr-log.md` (appended entry via Write Contract)
- **Session State**: Notes decision in active feature session notes `.corezero/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight & Decision Need Identification**:
   - Identify decision scope. Confirm that material trade-offs exist between at least two viable options.

2. **Comparative Evaluation**:
   - Research and compare at least two options across complexity, maintenance cost, performance, and team familiarity dimensions.
   - Apply `core-zero/rules/ponytail.md` (Simplicity Ladder: native features > standard library > installed deps > custom code) and `skills/spec-plan/references/deep-modules.md`.
   - Apply the deletion test and Design-it-Twice technique: compare interface depth, seam placement, blast radius, and test surface for both options.
   - Classify reversibility (`Easy | Moderate | Hard`). Prefer easy-to-reverse options when uncertainty remains.

3. **Draft Decision Record**:
   - Scaffold ADR: Run `python3 core-zero/scripts/core/cli.py adr-generate --title "<title>"` or create `core-zero/project/adr/[number]-[slug].md`.
   - Populate problem statement, evaluated options with pros/cons, decision outcome, and long-term consequences using `references/adr-template.md` or `references/adr-lightweight-template.md`.

4. **Append to ADR Log Ledger**:
   - Update `core-zero/memories/repo/adr-log.md` by appending a new entry conforming to its `## Entry Template`.
   - Record status as `Proposed` or `Accepted`. Link entry to `spec.md` or `plan.md`.

5. **Handoff & Terminal Return**:
   - Return control to the calling lifecycle skill (`/spec-plan`, `/spec-requirements`, or `/spec-implement`).

## Anti-Patterns & Red Flags

- **Single-Option ADR**: Documenting a decision without evaluating at least one viable alternative.
- **Silent Architecture Shift**: Changing major components or database choices without producing an ADR.
- **Retroactive Deletion**: Deleting or editing past accepted ADRs instead of marking them `Superseded` by a new ADR.

## Core Rules

- **Write Authority**: `/spec-adr` is the sole skill authorized to append entries to `core-zero/memories/repo/adr-log.md`.
- **Comparative Analysis**: Every ADR MUST evaluate at least two distinct options with depth, seam, blast radius, and reversibility.
- **Immutability**: Once `Accepted`, past ADR log entries are immutable. Superseded decisions MUST create a new ADR.
- **Design-it-Twice is not an ADR**: Interface comparison in `plan.md` does not replace this skill when the choice is hard to reverse.
