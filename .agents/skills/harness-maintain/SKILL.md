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
| **Reads** | `manifest.json`, `harness-config.yaml`, `core-policies.md` |
| **Writes** | Optional: `learned-heuristics.md` drafts, user-approved fixes |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py doctor --json`, `python3 corebase-specharness/scripts/core/cli.py gate-check --json`, `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug>` |
| **Entry** | Direct peer skill; return to caller after the bounded procedure |

## Overview

Interpret harness diagnostics, check manifest drift, validate gates, draft heuristics from failures, diagnose agent quality. CLI owns mechanical inspection; this skill owns prioritization and user-approved actions.

## When to Use & Invocation Triggers

- **When to Use**: harness health / drift / orphans; scaffold missing dirs; process `verify`/`gate-check` findings; diagnose agent quality.
- **Triggers**: `maintain harness`, `harness health`, `diagnose harness`, `improve harness`

## Execution Modes & Profiles

| Mode | Trigger | Focus |
|---|---|---|
| `assess` | Periodic / post-install | Manifest drift, orphans, config health |
| `create` | Missing infrastructure | Scaffold `memories/domain/` and placeholders |
| `improve` | Diagnostic failures | Draft `[DRAFT]` heuristics from findings |
| `eval` | Release candidate | `CC-*` sequentiality, manifest, gates |
| `doctor` | Fix mode | Assess + Markdown links + clean `doctor` |
| `diagnose` | Quality degradation | Symptom → fix via `references/diagnosis-map.md` |

## I/O & Artifact Protocol

- **Reads**: `manifest.json`, `harness-config.yaml`, `core-policies.md`.
- **Writes**: `learned-heuristics.md` `[DRAFT]` entries; user-approved config/policy edits.
- **Session**: N/A (repo-level).

## Step-by-Step Execution Workflow

1. **Select mode**: `assess`, `create`, `improve`, `eval`, `doctor`, or `diagnose`.

2. **Execute**:
   - *Assess*: `python3 corebase-specharness/scripts/core/cli.py doctor --json`. Diff `manifest.json` vs tree. Validate `harness-config.yaml`. Detect feature dirs lacking `status.md`.
   - *Create*: scaffold missing standard dirs or placeholders.
   - *Improve*: review `verify` / `gate-check`. Draft `[DRAFT]` entries; do not promote automatically.
   - *Eval*: audit `CC-*` sequentiality. Run `python3 corebase-specharness/scripts/core/cli.py verify --feature <slug>` or `python3 corebase-specharness/scripts/core/cli.py doctor`. Compare manifest vs tree.
   - *Doctor*: Assess + check links in `skills/*/*.md` + re-run `python3 corebase-specharness/scripts/core/cli.py doctor --json`.
   - *Diagnose*: match symptom to `references/diagnosis-map.md`; propose targeted policy/heuristic fixes.

3. **Approve & close**:
   - Present drafts for explicit user approval.
   - Report repaired items and remaining manual work.

## Anti-Patterns & Red Flags

- Promoting `[DRAFT]` or editing `core-policies.md` without review.
- Editing Python engine files instead of manifest/config.
- Shipping without `eval` manifest consistency.

## Core Rules

- `improve` drafts `[DRAFT]` only — user review REQUIRED before promotion.
- Releases require `eval` for 100% manifest consistency.
- CLI owns inspection; this skill owns recommendations.
- Failed gates need a fast, deterministic, red-capable command before a permanent heuristic.
- Periodically prune obsolete constraints.
