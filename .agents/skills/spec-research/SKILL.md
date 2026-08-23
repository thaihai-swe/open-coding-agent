---
id: skill-spec-research
name: spec-research
description: "Investigate a problem, feature area, bug, or brownfield subsystem and produce one bounded analysis artifact grounded in repository evidence. Use when root cause is unknown or current behavior must be mapped first."
tags: ['spec', 'research', 'exploration', 'root-cause', 'kaizen']
triggers: ['research', 'explore', 'brownfield', 'unknown', 'incident', '5 whys']
---
# Spec Research

## At a Glance

| | |
|---|---|
| **Reads** | `architecture.md`, codebase, domain packs, `status.md` |
| **Writes** | Required: `analysis.md`. Optional: `status.md`. Session: `.corebase-specharness/sessions/<slug>/session.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-research --feature <slug> --intent "<request>"`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-research --feature <slug> --handoff spec-requirements` |
| **Suggested Handoff** | `/spec-requirements` |

## Overview

Produce `analysis.md` from repository evidence. Use for bugs, failure tracing, and brownfield mapping before spec or plan.

## When to Use & Invocation Triggers

- **When to Use**: unknown current behavior; diagnose/reproduce bugs; map brownfield boundaries.
- **Triggers**: `research`, `explore`, `brownfield`, `unknown`, `incident`, `5 whys`

## Execution Modes & Profiles

| Mode | Trigger | Output |
|---|---|---|
| `bug-diagnosis` | Bug, regression, failing test | Red-capable command + 5-whys in `analysis.md` |
| `brownfield-map` | Unknown legacy / broad area | Files, deps, risks, preserved contracts |
| `ambiguity-resolution` | Contested design | ADI cycle + throwaway prototype |

## I/O & Artifact Protocol

- **Reads**: `status.md`, `architecture.md`, target source, domain packs.
- **Writes**: `analysis.md` (`## Findings`, `## High Risk Paths`, `## Open Questions`, `## Kaizen Countermeasures`); `status.md` (`Researching` → `ResearchComplete`).
- **Session**: `.corebase-specharness/sessions/<slug>/session.md`.

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-research --feature <slug> --intent "<request>"`.
   - Omit `--full` unless compacted, new chat on existing feature, reload requested, or pack stale. See `skills/_shared/context-loading.md`.
   - Do not hand-edit `- Phase:`.

2. **Context**:
   - Pass request as `--intent`. Domain packs match `triggers:` in `corebase-specharness/memories/domain/<name>/glossary.md`; note any loaded pack in `status.md`.

3. **Execute (pick mode)**:
   - *Bug Diagnosis*:
     - Phase 1 hard gate: name one already-run command that is red on this exact bug — deterministic, seconds, agent-runnable. No hypothesis until it exists. If none → `[:HALT INCONCLUSIVE]`.
     - Minimise until every remaining element is load-bearing.
     - 3–5 ranked falsifiable hypotheses: `"If <X> is the cause, changing <Y> makes the bug disappear / changing <Z> makes it worse."` Show before instrumenting.
     - Instrument one variable at a time. Tag logs `[DEBUG-<id>]`. Record root cause and 5-Whys via `references/debugging-checklist.md` (`## Root Cause Record`).
     - Remove `[DEBUG-<id>]` or note it. Delete or mark throwaway harness.
   - *Ambiguity*: ADI cycle via `references/analysis-template.md` (`## Architecture / Design Investigation (ADI) Template`). Prototypes per `references/debugging-checklist.md` (`## Prototype Technique`).
   - *Brownfield*: deps, contracts, reuse, migration. Use `references/analysis-template.md` (`## Zoom-Out Prompt`).

4. **Author**:
   - Write `analysis.md` via `references/analysis-template.md`. MUST include `## Findings`, `## High Risk Paths`, `## Open Questions`, `## Kaizen Countermeasures`, plus `## Metadata` and `## Recommendation & Next Step`.

5. **Handoff**:
   - Sparse evidence → `[:HALT INCONCLUSIVE]`.
   - Else `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-research --feature <slug> --handoff spec-requirements`.
   - Use `--handoff spec-adr` when a contested architectural choice blocks requirements.

## Anti-Patterns & Red Flags

- Claiming root cause without a red-capable command.
- Writing production code or plans in research.
- Notes that ignore the `analysis.md` schema.

## Core Rules

- Separate facts from inferences; prove hypotheses with code.
- Research produces analysis only. Code belongs to `/spec-implement`.
- No custom unmapped artifacts.
