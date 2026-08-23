---
id: skill-starter-init
name: starter-init
description: "Bootstrap a new repository with CoreBase SpecHarness memory scaffolding, archaeology sweep, and confirmed gate setup for harnessed agentic development."
tags: ['setup', 'init', 'onboarding']
triggers: ['init', 'start', 'setup', 'install']
---
# Starter Init

## At a Glance

| | |
|---|---|
| **Reads** | Target repo structure, `harness-config.yaml` (seed template) |
| **Writes** | Optional directories: `corebase-specharness/project`, `corebase-specharness/memories/repo` (adopter seeds only) |
| **Key CLI** | `python3 corebase-specharness/scripts/core/cli.py init --json`, `python3 corebase-specharness/scripts/core/cli.py doctor --json`, `python3 corebase-specharness/scripts/core/cli.py memory-audit --json` |
| **Entry** | Direct peer skill; choose `/spec-research` or `/spec-requirements` after bootstrap |

## Overview

Bootstrap `corebase-specharness/` directories and customize memory seeds for the project. Detects repo type, guides read-only archaeology for brownfields, and establishes verification gates.

## When to Use & Invocation Triggers

- **When to Use**: newly installed repo; setup memory/policies/gates; resync stack drift.
- **Triggers**: `init`, `start`, `setup`, `install`

## Execution Modes & Profiles

| Mode | Condition | Outputs |
|---|---|---|
| `fresh-init` | Empty / uninitialized workspace | 4-step bootstrap: scaffold, Phase A sweep, Phase B memory, gates |
| `resync-drift` | `harness-config.yaml` exists | Read-only diff pass vs `tech-stack.md` |

## I/O & Artifact Protocol

- **Reads**: Target repo codebase, stack markers (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.).
- **Writes**: `core-policies.md`, `project-knowledge-base.md`, `learned-heuristics.md`, `architecture.md`, `tech-stack.md`, `harness-config.yaml`.
- **Session**: N/A for bootstrap phase.

## Step-by-Step Execution Workflow

1. **Pre-flight & Scaffold**:
   - `python3 corebase-specharness/scripts/core/cli.py init --json`.
   - Inspect existing `AGENTS.md` and native instruction files; preserve valid rules and surface conflicts.
   - Read `onboarding_readiness` from `init --json` (stacks, gates, preserved files, `[UNKNOWN]` facts).

2. **Archaeology Sweep (Phase A)**:
   - Detect stack markers (`package.json`→node, `pyproject.toml`→python, `go.mod`→go, `Cargo.toml`→rust). Record in `tech-stack.md`.
   - *Greenfield*: empty repo → skip archaeology.
   - *Brownfield*: follow `references/brownfield-mode.md` for read-only sweep. Record in `tech-stack.md`, `architecture.md`, `core-policies.md` (`## Known Broken Tests`, `## Security Policy`), and `project-knowledge-base.md` (`## Preserved Behavior Baseline`).

3. **Memory Customization & Gates (Phase B)**:
   - Discover stack, entrypoints, existing gates via inspection; ask adopter only for identity, SLOs, trust boundaries, gate confirmation.
   - Ask unblocked questions in one numbered batch with recommended defaults.
   - Pre-fill seeded files using `references/template-prefill.md`. Mark gaps `[UNKNOWN]` or `[USER REVIEW NEEDED]`.
   - Confirm/edit:
     - `core-policies.md`: normative rules, `## Known Broken Tests`, `## Security Policy`.
     - `project-knowledge-base.md`: `## Preserved Behavior Baseline` and watchouts.
     - `learned-heuristics.md`: keep project-relevant entries.
     - `harness-config.yaml`: write build/lint/test gates, set `project_setup.status: ready` + `reviewed_at`. If deferred, explain no-gate advisory cannot close features.
     - `glossary.md`: capture domain terms immediately.

4. **Verification & Handoff**:
   - `python3 corebase-specharness/scripts/core/cli.py doctor --json`.
   - `python3 corebase-specharness/scripts/core/cli.py memory-audit --json`.
   - Report onboarding readiness: confirmed facts, unknowns, gates, conflicts, next skill.
   - External onboarding docs: see `EXTERNAL_SKILLS.md`.
   - Handoff to `/spec-research` (brownfield) or `/spec-requirements` (greenfield).

## Anti-Patterns & Red Flags

- Leaving kit placeholders as project memory.
- Overwriting adopter policies on re-run.
- Writing custom engine scripts instead of registering gates in `harness-config.yaml`.
- Modifying source code during Phase A.

## Core Rules

- Phase B customization MUST be completed or explicitly marked `[DEFERRED]`.
- Mark missing facts `[UNKNOWN]` per CC-002; never guess.
- Look up facts; ask only decisions.
- Preserve headings and IDs (`CC-*`, `LH-*`).
- Summarize subagent listings before merging into context.
- `AGENTS.md` is the canonical shipped router.
