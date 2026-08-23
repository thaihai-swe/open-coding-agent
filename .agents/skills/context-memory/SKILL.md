---
id: skill-context-memory
name: context-memory
description: "Maintain repository memory through evidence-backed updates, promotion, audit, and safe compaction."
tags: ['context', 'memory', 'heuristics', 'compaction']
triggers: ['memory', 'heuristic', 'learned', 'update memory', 'compact', 'compress', 'memory full', 'token budget']
---
# Context Memory

## At a Glance

| | |
|---|---|
| **Reads** | `core-policies.md`, `learned-heuristics.md`, `project-knowledge-base.md`, `session-extracts.md`, `MASTER_INDEX.md` |
| **Writes** | Optional: `corebase-specharness/memories/repo/`, `corebase-specharness/memories/domain/`, `session-extracts.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py memory-audit --json`, `python3 corebase-specharness/scripts/core/cli.py memory-gate --json`, `python3 corebase-specharness/scripts/core/cli.py session-end --feature <slug>` |
| **Entry** | Direct peer skill; return to caller after the bounded procedure |

## Overview

Maintain durable memory so later agents do not repeat mistakes. Modes: post-ship sync, audit, compaction, decay.

## When to Use & Invocation Triggers

- **When to Use**: after `/harness-verify` writes `## Post-Ship Sync` and exits `Done`; triage `[CANDIDATE]` items; audit size; compact over-budget files.
- **Triggers**: `memory`, `heuristic`, `learned`, `update memory`, `compact`, `compress`, `memory full`, `token budget`

## Execution Modes & Profiles

| Mode | Trigger | Output |
|---|---|---|
| `post-ship-sync` | Passing verify | Sweep extracts; promote triaged candidates |
| `audit-mode` | `memory-audit` / budget debug | Line counts, tokens, threshold breaches |
| `compaction-mode` | Over line/token threshold | Cut prose 30–50%; keep `##` headings and `LH-*`/`CC-*` |
| `decay-archival` | Outdated LH-* | Move to `deprecated-heuristics.md` |

## I/O & Artifact Protocol

- **Reads**: `session-extracts.md`, `MASTER_INDEX.md`, `core-policies.md`, `learned-heuristics.md`, `project-knowledge-base.md`.
- **Writes**: `learned-heuristics.md` (`LH-*`); PKB; `core-policies.md` (`CC-*`); domain `patterns.md`; `deprecated-heuristics.md`.
- **Session**: mark extracts triaged; `session-end`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py memory-audit --json`.
   - `python3 corebase-specharness/scripts/core/cli.py memory-gate --json`.

2. **Mode**:
   - *Post-Ship Sync*: process every `[CANDIDATE]` per `references/extraction-triage.md`. Promote only with recurrence or independent evidence. Merge duplicates. Stamp `<!-- triaged: true, date: YYYY-MM-DD -->`.
   - *Audit*: report size/token findings. Doc drift → `EXTERNAL_SKILLS.md`.
   - *Compact*: snapshot `<file>.bak` and `<file>.ids_before`. Cut 30–50% to bullets without rewriting meaning. Keep every `##` heading and stable ID (`LH-*`, `CC-*`, `INV-*`, `ADR-*`, `T-*`, `REQ-*`, `AC-*`). Halt if `.ids_after` ≠ `.ids_before`. Stop if draft would cut >60%.
   - *Decay*: keep `LH-*` heading, mark `[ARCHIVED]`, append body to `deprecated-heuristics.md`. Do not reuse IDs.

3. **Verify & close**:
   - Re-run `python3 corebase-specharness/scripts/core/cli.py memory-audit --json`.
   - `python3 corebase-specharness/scripts/core/cli.py session-end --feature <slug>`.

## Anti-Patterns & Red Flags

- Promoting single-session noise without recurrence.
- Deleting `LH-*`/`CC-*` during compaction.
- Cutting >60% of prose.
- Splitting files without `promotions.md`.

## Core Rules

- Promoted edits MUST trace to a recorded observation.
- Single-session items are deferred unless hard safety/data-loss.
- Stable IDs MUST NEVER be deleted during compaction.
- Record only observed facts.
