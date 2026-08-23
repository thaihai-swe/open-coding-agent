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
| **Reads** | `corebase-specharness/project/architecture.md`, codebase files, domain packs, `status.md` |
| **Writes** | Required: `analysis.md`. Optional: `status.md`. Session: `.corebase-specharness/sessions/<slug>/session.md` |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-research --feature <slug> --intent "<request>"`, `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-research --feature <slug> --handoff spec-requirements` |
| **Suggested Handoff** | `/spec-requirements` |

## Overview

Investigate system behaviors and produce `artifacts/features/<slug>/analysis.md`. Use this for debugging, failure tracing, and mapping brownfield code before writing a spec or plan.

Acts as the discovery engine of CoreBase SpecHarness, ensuring evidence-backed findings and kaizen root-cause analysis guide downstream requirements.

## When to Use & Invocation Triggers

- **When to Use**:
  - Understanding existing behavior before writing a spec or plan.
  - Diagnosing, reproducing, and isolating bugs or regressions.
  - Mapping boundaries, dependencies, and preserved behaviors in brownfield subsystems.
- **Triggers**: `research`, `explore`, `brownfield`, `unknown`, `incident`, `5 whys`

## Execution Modes & Profiles

| Mode | Trigger / Condition | Primary Purpose & Outputs |
|---|---|---|
| `bug-diagnosis` | Bug report, regression issue, or test failure | Recreates failure seam with a red-capable command, 5-whys root cause analysis in `analysis.md` |
| `brownfield-map` | Unknown legacy subsystem or broad feature area | Maps target files, trace dependencies, risks, and preserved contracts |
| `ambiguity-resolution` | Contested algorithm or high-risk design question | Falsifies hypotheses using ADI cycle and throwaway prototype scripts |

## I/O & Artifact Protocol

- **Reads**: `artifacts/features/<slug>/status.md`, `corebase-specharness/project/architecture.md`, target source code, domain packs (`corebase-specharness/memories/domain/<name>/glossary.md`).
- **Writes**:
  - `artifacts/features/<slug>/analysis.md` (containing `## Findings`, `## High Risk Paths`, `## Open Questions`, and `## Kaizen Countermeasures`)
  - `artifacts/features/<slug>/status.md` via `skill-enter` (`Researching`) and `skill-exit` (`ResearchComplete`)
- **Session State**: Updates `.corebase-specharness/sessions/<slug>/session.md` (`## Objective`, `## Progress`, `## Handoff`).

## Step-by-Step Execution Workflow

1. **Pre-flight**:
   - Run `python3 corebase-specharness/scripts/core/cli.py skill-enter --skill spec-research --feature <slug> --intent "<request>"`.
   - Omit `--full` unless this conversation was compacted, this is the first skill in a new chat on an existing feature, the user asked to reload context, or the pack is known stale. See `skills/_shared/context-loading.md`.
   - Do not hand-edit `- Phase:`. The envelope creates `status.md` if needed and sets `Researching`.

2. **Context & Domain Alignment**:
   - Supply the feature request as `--intent` to context loading. CoreBase SpecHarness discovers nested domain packs by matching that intent against `triggers:` in `corebase-specharness/memories/domain/<name>/glossary.md`; note any loaded pack in `status.md`.

3. **Execution (Select Mode)**:
   - *Bug Diagnosis Loop*:
     - **Phase 1 — Tight Feedback Loop (hard gate)**: Name one command (test, script, or curl) that has already been run and goes **red on this exact bug**. The command must be red-capable (asserts the user's symptom), deterministic, fast (seconds), and agent-runnable. No hypothesis is formed until this command exists. If no loop can be built after exhausting all options, write `[:HALT INCONCLUSIVE]` and list what was tried.
     - **Minimise**: Shrink the repro until every remaining element is load-bearing; removing any one makes the loop go green.
     - **Hypothesise**: Generate 3–5 ranked falsifiable hypotheses before testing any: `"If <X> is the cause, changing <Y> makes the bug disappear / changing <Z> makes it worse."` Show to the user before instrumentation.
     - **Instrument**: One variable at a time. Tag all temporary debug logs `[DEBUG-<id>]` for surgical cleanup. Document confirmed root cause and Kaizen 5-Whys in `analysis.md` using `references/debugging-checklist.md` (`## Root Cause Record`).
     - **Cleanup**: All `[DEBUG-<id>]` instrumentation removed or noted before exit. Throwaway harness deleted or marked.
   - *Ambiguity Resolution*: Apply Abduction-Deduction-Induction (ADI) reasoning cycle using `references/analysis-template.md` (`## Architecture / Design Investigation (ADI) Template`). Use throwaway prototype scripts per `references/debugging-checklist.md` (`## Prototype Technique`) to resolve logic questions.
   - *Brownfield Mapping*: Trace dependencies, boundary contracts, reuse patterns, and migration constraints. Use `references/analysis-template.md` (`## Zoom-Out Prompt`) to step up abstraction level.

4. **Artifact Authoring**:
   - Write all findings to `artifacts/features/<slug>/analysis.md` using `references/analysis-template.md`. MUST include: `## Findings`, `## High Risk Paths`, `## Open Questions`, `## Kaizen Countermeasures`. Also write `## Metadata` and `## Recommendation & Next Step`.

5. **Handoff**:
   - If evidence is too sparse to conclude, write `[:HALT INCONCLUSIVE]` in `analysis.md` and escalate to user.
   - Otherwise run `python3 corebase-specharness/scripts/core/cli.py skill-exit --skill spec-research --feature <slug> --handoff spec-requirements`.
   - Use `--handoff spec-adr` when a contested architectural choice blocks requirements.

## Anti-Patterns & Red Flags

- **Vibe Diagnosing**: Claiming a bug root cause without a red-capable command asserting the failure seam.
- **Scope Creep (Writing Code)**: Writing production feature code or technical plans inside research phase.
- **Unstructured Findings**: Writing arbitrary notes instead of strict `analysis.md` schema sections.

## Core Rules

- **Fact-Focused**: Separate observed facts from inferences; prove hypotheses with code evidence.
- **Scope Boundary**: Research phase produces analysis only — code modifications belong to `/spec-implement`.
- **Strict Artifact Schema**: Do not create custom unmapped artifacts outside designated paths.
