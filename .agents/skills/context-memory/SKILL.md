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
| **Entry** | Directly invokable peer skill; return to the caller after the bounded procedure |

## Overview

Maintains persistent project and repository memories (`learned-heuristics.md`, `project-knowledge-base.md`, `core-policies.md`, domain packs) so future AI agents don't repeat past mistakes.

Governs four operational modes: Regular Memory Updates, Audit Mode, Post-Ship Sync Mode, and Compaction Mode.

## When to Use & Invocation Triggers

- **When to Use**:
  - Post-ship promotion after `/harness-verify` writes `## Post-Ship Sync` and exits to `Done`.
  - Triaging candidate lessons (`[CANDIDATE]`) from `session-extracts.md`.
  - Auditing memory files for size and token-budget breaches.
  - Safely compacting oversized memory files that exceed token budget thresholds.
- **Triggers**: `memory`, `heuristic`, `learned`, `update memory`, `compact`, `compress`, `memory full`, `token budget`

## Execution Modes & Profiles

| Mode | Condition / Trigger | Primary Purpose & Outputs |
|---|---|---|
| `post-ship-sync` | Triggered by `/harness-verify` upon passing verdict | Sweeps `session-extracts.md`, promotes triaged `[CANDIDATE]` items, updates memory logs |
| `audit-mode` | Invoked via `memory-audit` or when debugging memory budget | Reads `python3 corebase-specharness/scripts/core/cli.py memory-audit --json`, reports line counts, token estimates, and threshold breaches |
| `compaction-mode` | File exceeds line/token threshold (via `python3 corebase-specharness/scripts/core/cli.py memory-gate`) | Reduces prose by 30-50% while preserving every `##` heading and stable ID (`LH-*`, `CC-*`) |
| `decay-archival` | LH-* heuristics flagged as outdated or superseded | Moves tombstoned heuristics to `corebase-specharness/memories/archive/deprecated-heuristics.md` |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/session-extracts.md`, `corebase-specharness/MASTER_INDEX.md`, `corebase-specharness/memories/repo/core-policies.md`, `corebase-specharness/memories/repo/learned-heuristics.md`, `corebase-specharness/memories/repo/project-knowledge-base.md`.
- **Writes**:
  - `corebase-specharness/memories/repo/learned-heuristics.md` (`LH-*`)
  - `corebase-specharness/memories/repo/project-knowledge-base.md`
  - `corebase-specharness/memories/repo/core-policies.md` (`CC-*`)
  - `corebase-specharness/memories/domain/<name>/patterns.md`
  - `corebase-specharness/memories/archive/deprecated-heuristics.md`
- **Session State**: Marks candidates as triaged in `session-extracts.md` and closes active session.

## Step-by-Step Execution Workflow

1. **Pre-flight & Mechanical Pre-flight**:
   - Run `python3 corebase-specharness/scripts/core/cli.py memory-audit --json` to inspect file sizes, line counts, token estimates, and threshold warnings.
   - Run `python3 corebase-specharness/scripts/core/cli.py memory-gate --json` to verify budget compliance.

2. **Mode Execution**:
   - *Post-Ship Sync*: Read `session-extracts.md`. Process every `[CANDIDATE]` entry per `references/extraction-triage.md`. Decide promote, defer, or discard for each item. Promote confirmed lessons (LH-* to `learned-heuristics.md`, CC-* to `core-policies.md`, patterns to PKB) only when recurrence or independent evidence exists. Merge semantic duplicates instead of appending a second rule. Stamp `<!-- triaged: true, date: YYYY-MM-DD -->`.
   - *Audit Mode*: Produce structured report citing size/token findings. If documentation drift is found, recommend the optional external-skills guide (`EXTERNAL_SKILLS.md`).
   - *Compaction Mode*: Create safety snapshot (`<file>.bak` and `<file>.ids_before`). Reduce prose by 30–50% converting prose to bullets. Do not rewrite meaning. Preserve every `##` heading and every stable ID (`LH-*`, `CC-*`, `INV-*`, `ADR-*`, `T-*`, `REQ-*`, `AC-*`). Extract IDs with the same pattern before and after; halt if `<file>.ids_after` does not match `ids_before` exactly. Stop if the draft would cut more than 60% of prose.
   - *Decay Action*: Tombstone archived heuristics in `learned-heuristics.md` (keep the `LH-*` heading, mark `[ARCHIVED]`) and append the full body to `corebase-specharness/memories/archive/deprecated-heuristics.md`. Do not reuse retired IDs.

3. **Verification & Handoff**:
   - Re-run `python3 corebase-specharness/scripts/core/cli.py memory-audit --json` to confirm size compliance.
   - Close feature session: Run `python3 corebase-specharness/scripts/core/cli.py session-end --feature <slug>`.

## Anti-Patterns & Red Flags

- **Unverified Promotion**: Promoting single-session noise into global `core-policies.md` without recurrence proof.
- **Deleting Stable IDs**: Removing an `LH-*` or `CC-*` ID during compaction (breaks traceability logs).
- **Over-Compaction (>60%)**: Stripping normative intent or code boundaries instead of presentation.
- **Silent File Splitting**: Splitting memory files without writing a promotion proposal to `artifacts/features/<slug>/promotions.md`.

## Core Rules

- **Evidence-Backed**: Every promoted heuristic or policy edit MUST trace to a recorded observation or session extract.
- **Recurrence Before Promotion**: A single-session observation is deferred unless the lesson is a hard safety or data-loss rule.
- **ID Immutability**: Stable identifiers (`CC-*`, `LH-*`, `INV-*`, `ADR-*`, `T-*`, `REQ-*`, `AC-*`) MUST NEVER be deleted during compaction.
- **No Fabrication**: Record only observed repository facts — never invent hypothetical guidelines.
