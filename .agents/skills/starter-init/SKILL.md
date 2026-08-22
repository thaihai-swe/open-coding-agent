---
id: skill-starter-init
name: starter-init
description: "Bootstrap a new repository with CoreZero memory scaffolding, archaeology sweep, and confirmed gate setup for harnessed agentic development."
tags: ['setup', 'init', 'onboarding']
triggers: ['init', 'start', 'setup', 'install']
---
# Starter Init

## At a Glance

| | |
|---|---|
| **Reads** | Target repo structure, `core-zero/project/harness-config.yaml` (seed template) |
| **Writes** | Optional directories: `core-zero/project`, `core-zero/memories/repo` (adopter-owned seeds only) |
| **Key CLI** | `python3 core-zero/scripts/core/cli.py init --json`, `python3 core-zero/scripts/core/cli.py doctor --json`, `python3 core-zero/scripts/core/cli.py memory-audit --json` |
| **Entry** | Directly invokable peer skill; choose `/spec-research` or `/spec-requirements` after bootstrap |

## Overview

Bootstraps the `core-zero/` and `core-zero/memories/` directories with standard templates, then guides the adopter through customizing the seeded memory files for their project.

Establishes the repository baseline for the harness before feature work begins. Detects repo type, guides a read-only archaeology pass for brownfield repositories, and sets up the initial memory scaffold with adopter-specific content. Archaeology is an agent-run skill workflow, not installer-side automatic behavior.

## When to Use & Invocation Triggers

- **When to Use**:
  - Bootstrapping a newly installed or cloned repository.
  - Setting up project-level memory, policies, architecture, and verification gates.
  - Resynching stack markers and archaeology findings on a previously initialized repo.
- **Triggers**: `init`, `start`, `setup`, `install`

## Execution Modes & Profiles

| Mode | Condition / Trigger | Primary Purpose & Outputs |
|---|---|---|
| `fresh-init` | Empty repo or uninitialized workspace | Complete 4-step bootstrap: scaffolding, Phase A sweep, Phase B memory pre-fill, gate setup |
| `resync-drift` | `harness-config.yaml` exists and is non-empty | Read-only archaeology diff pass; outputs drift report against `tech-stack.md` without overwriting adopter edits |

## I/O & Artifact Protocol

- **Reads**: Target repository codebase, stack markers (`package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, etc.).
- **Writes**:
  - `core-zero/memories/repo/core-policies.md`
  - `core-zero/memories/repo/project-knowledge-base.md`
  - `core-zero/memories/repo/learned-heuristics.md`
  - `core-zero/project/architecture.md`
  - `core-zero/project/tech-stack.md`
  - `core-zero/project/harness-config.yaml`
  - (Brownfield only): `core-zero/memories/repo/brownfield/brownfield-map.md`
- **Session State**: N/A for bootstrap phase; prepares workspace for session initialization.

## Step-by-Step Execution Workflow

1. **Pre-flight & Scaffold Initialization**:
   - Run `python3 core-zero/scripts/core/cli.py init --json` for directory, seed-file, stack-marker, and `.gitignore` mechanics.
   - Inspect existing `AGENTS.md` and any native agent instruction files. `AGENTS.md` is the portable CoreZero router; preserve native files and surface conflicts rather than creating or editing them.
   - Read the `onboarding_readiness` section returned by `python3 core-zero/scripts/core/cli.py init --json`. It identifies detected stacks, confirmed gates, preserved instruction files, and `[UNKNOWN]` onboarding facts.

2. **Archaeology Sweep (Phase A)**:
   - Detect greenfield vs. brownfield using stack markers (`package.json`→node, `pyproject.toml`→python, `go.mod`→go, `Cargo.toml`→rust, etc.). Record hits in `core-zero/project/tech-stack.md`.
   - *Greenfield*: If empty repo or kit-only files, skip archaeology pass.
   - *Brownfield*: Follow `references/brownfield-mode.md` to conduct a read-only archaeology sweep using subagents. Write findings to `core-zero/memories/repo/brownfield/brownfield-map.md`. Record baseline test command and high-risk paths. Option: use `references/rules-bootstrap.md` for convention proposals.

3. **Memory Customization & Gate Setup (Phase B)**:
   - Separate facts from decisions. Discover stack, entrypoints, existing gates, and instruction files through inspection; ask the adopter only for product identity, SLOs, trust boundaries, and gate confirmation.
   - Ask unblocked onboarding questions in one numbered frontier batch with a recommended default per question. Do not invent missing facts.
   - Pre-fill seeded files from evidence using `references/template-prefill.md`. Mark remaining gaps `[UNKNOWN]` or `[USER REVIEW NEEDED]`.
   - Interactively confirm or rewrite:
     - `core-policies.md`: Set project identity, default branch, verification commands, and security trust boundaries.
     - `project-knowledge-base.md`: Record components, integration boundaries, and ubiquitous domain jargon.
     - `learned-heuristics.md`: Clean kit-internal heuristics; keep project-relevant entries.
     - `harness-config.yaml`: Write adopter build/lint/test commands under configured gate runner commands, then set `project_setup.status: ready` and `reviewed_at` after the adopter confirms them. If deferred, retain `deferred` and explain that no-gate advisory verification cannot normally close a feature.
     - `core-zero/project/glossary.md`: Capture resolved domain terms immediately; do not invent vocabulary.

4. **Mechanical Verification & Handoff**:
   - Run `python3 core-zero/scripts/core/cli.py doctor --json` to verify manifest and context routes.
   - Run `python3 core-zero/scripts/core/cli.py memory-audit --json` to inspect durable-memory size and duplication.
   - Report the onboarding readiness summary: confirmed facts, `[UNKNOWN]` facts, proposed/confirmed gates, instruction-file conflicts, and the next explicit delivery skill.
   - If repository onboarding documentation is needed, direct the adopter to `EXTERNAL_SKILLS.md`; external skills are optional and are not CoreZero routes.
   - Hand off to `/spec-research` (brownfield) or `/spec-requirements` (greenfield).

## Anti-Patterns & Red Flags

- **Skipping Phase B Customization**: Leaving generic kit placeholders masquerading as project memory.
- **Destructive Re-Init**: Overwriting custom adopter policies or architecture notes during a re-run.
- **Shadow Installer**: Writing custom engine scripts instead of registering configured gate commands in `harness-config.yaml`.
- **Modifying Source Code**: Editing codebase files during read-only Phase A archaeology sweep.

## Core Rules

- **Mandatory Customization**: Phase B customization MUST be completed or explicitly deferred with `[DEFERRED]`.
- **Ask, Don't Guess**: Record explicit evidence or adopter answers; mark `[UNKNOWN]` per CC-003 when details are unavailable.
- **Fact vs Decision**: Look up repository facts; ask only product, policy, and gate decisions.
- **Surgical Memory Edits**: Preserve headings and ID structures (`CC-*`, `LH-*`).
- **Subagent Summaries Only**: Raw subagent listings must be summarized before merging into main context.
- **Portable Router**: `AGENTS.md` is the canonical shipped router. CoreZero does not generate or require vendor-specific agent configuration files.
