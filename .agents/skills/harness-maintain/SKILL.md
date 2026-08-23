---
id: skill-harness-maintain
name: harness-maintain
description: "Interpret deterministic harness diagnostics and propose bounded maintenance actions."
tags: ['harness', 'maintenance', 'diagnostics']
triggers: ['maintain harness', 'harness health', 'diagnose harness', 'improve harness']
---
# Harness Maintain

## At a Glance

| | |
|---|---|
| **Reads** | `manifest.json`, `corebase-specharness/project/harness-config.yaml`, `corebase-specharness/generated/gate-runs.json` (when present), `core-policies.md` |
| **Writes** | Optional: `corebase-specharness/generated/harness-assessment.md`, `learned-heuristics.md` drafts, user-approved fixes |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py doctor --json`, `python3 corebase-specharness/scripts/core/cli.py gate-check --json`, `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug>` |
| **Entry** | Directly invokable peer skill; return to the caller after the bounded procedure |

## Overview

Interprets deterministic harness diagnostics, checks manifest drift, validates gate runner configurations, drafts learned heuristics from gate failures, and diagnoses agent quality issues.

The CLI script runtime owns mechanical inspection, validation, and generated outputs; this skill owns evidence-backed prioritization, quality diagnosis, and user-approved maintenance actions.

## When to Use & Invocation Triggers

- **When to Use**:
  - Assessing repository harness health, manifest drift, or orphaned artifacts.
  - Scaffolding missing standard directories or configuration placeholders.
  - Processing verification gate failures (`corebase-specharness/generated/gate-runs.json`) to draft self-healing heuristics.
  - Diagnosing agent execution failures or quality degradation.
- **Triggers**: `maintain harness`, `harness health`, `diagnose harness`, `improve harness`

## Execution Modes & Profiles

| Mode | Condition / Trigger | Primary Focus & Outputs |
|---|---|---|
| `assess` | Periodic check or post-install audit | Evaluates manifest drift, orphan artifacts, and config health; outputs `harness-assessment.md` |
| `create` | Missing infrastructure detected | Scaffolds missing standard directories (`corebase-specharness/generated/`, `memories/domain/`) |
| `improve` | Diagnostics failure analysis | Reviews failed entries in `corebase-specharness/generated/gate-runs.json` and drafts `[DRAFT]` heuristics |
| `eval` | Release candidate audit | Validates `CC-*` rule sequentiality, manifest consistency, and gate configurations |
| `doctor` | Maintenance fix mode | Runs assess mode, validates Markdown links, and confirms `doctor` remains clean |
| `diagnose` | Agent quality degradation reported | Maps failure symptoms to root causes and fixes using `references/diagnosis-map.md` |

## I/O & Artifact Protocol

- **Reads**: `manifest.json`, `corebase-specharness/project/harness-config.yaml`, `corebase-specharness/generated/gate-runs.json` (when present), `corebase-specharness/memories/repo/core-policies.md`.
- **Writes**:
  - `corebase-specharness/generated/harness-assessment.md` (health report)
  - `corebase-specharness/memories/repo/learned-heuristics.md` (appended `[DRAFT]` entries)
  - User-approved maintenance updates to harness configs or policies
- **Session State**: N/A (operates at repository harness level).

## Step-by-Step Execution Workflow

1. **Pre-flight & Mode Selection**:
   - Select mode (`assess`, `create`, `improve`, `eval`, `doctor`, or `diagnose`).

2. **Mode Execution Procedures**:
   - *Assess Mode*: Run `python3 corebase-specharness/scripts/core/cli.py doctor --json`. Check `manifest.json` against actual file tree. Validate `corebase-specharness/project/harness-config.yaml`. Detect orphan feature directories lacking `status.md`. Write `corebase-specharness/generated/harness-assessment.md`.
   - *Create Mode*: Read assessment report; scaffold missing standard directories or baseline placeholders.
   - *Improve Mode*: Review failed entries in `corebase-specharness/generated/gate-runs.json` when available. Draft evidence-backed `[DRAFT]` entries in `learned-heuristics.md`; do not promote them automatically.
   - *Eval Mode*: Audit `CC-*` identifiers in `core-policies.md` for sequentiality. Run `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug>` (or `python3 corebase-specharness/scripts/core/cli.py doctor`). Compare manifest against file tree.
   - *Doctor Mode*: Run Assess steps, check for broken links in `skills/*/*.md`, and re-run `python3 corebase-specharness/scripts/core/cli.py doctor --json`.
   - *Diagnose Mode*: Match reported failure symptom against `references/diagnosis-map.md`. Identify root cause category and propose targeted policy/heuristic fixes.

3. **User Approval & Closeout**:
   - Present drafted heuristics or configuration edits to user for explicit approval.
   - Report summary of repaired items and remaining manual maintenance tasks.

## Anti-Patterns & Red Flags

- **Silent Rule Promotion**: Finalizing `[DRAFT]` heuristics or editing `core-policies.md` without explicit user review.
- **Shadow Harness Edits**: Modifying python script engine files directly instead of updating manifest/config declarations.
- **Bypassing Manifest Checks**: Shipping package releases without running `eval` mode manifest consistency audits.

## Core Rules

- **No Silent Promotion**: `improve` mode drafts heuristics as `[DRAFT]` only — user review is REQUIRED before promotion.
- **Audit Before Release**: Package releases require running `eval` mode to ensure 100% manifest consistency.
- **CLI Mechanics Ownership**: CLI owns mechanical inspection; this skill owns evidence-backed recommendations.
- **Tight-Loop Gate Discovery**: When gate runners fail, ensure proposals include a fast, deterministic, red-capable command before drafting permanent heuristics.
- **Harness Pruning**: Periodically remove obsolete constraints and simplify harness rules when the model has mastered the underlying capability.
