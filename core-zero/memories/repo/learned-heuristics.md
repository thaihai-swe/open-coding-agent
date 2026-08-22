# Learned Heuristics

## Index

- LH-001 — Docs drift at workflow surface; update in same wave
- LH-002 — Bootstrap and docs verified together
- LH-003 — Generated references are worth seeding early [KIT — low relevance here]
- LH-004 — Agent overscaffolds new files [ARCHIVED — promoted to code-design.md]
- LH-005 — Vague task validation leads to skipped verification
- LH-006 — Token budget underestimation triggers mid-task compaction
- LH-007 — Memory thresholds trigger post-oversize; track proactively
- LH-008 — Domain packs ignored when building features [ARCHIVED — promoted to spec-requirements]
- LH-009 — Blueprint is not the running system
- LH-010 — Green unittest suite does not cover tool handlers

## Purpose

This file captures repeated, evidence-backed heuristics for this coding-agent repository. Kit-internal install heuristics that do not apply to `src/` are marked KIT.

## Heuristics

### LH-001: Docs drift fastest at the workflow surface
- Trigger:
  - a skill contract, CLI flag, or operator command in `documents/how-to-run.md` changes
- Working heuristic:
  - update `documents/how-to-run.md` and any cited example files in the same wave
- Evidence:
  - `how-to-run.md` still references missing `documents/config.example.json` and claims `.secrets/` is gitignored
- Confidence: High
- Last reviewed: 2026-04-08
- Promote to stronger rule? No

### LH-002: Bootstrap and docs must be verified together
- Trigger:
  - repo memory or operator bootstrap steps change
- Working heuristic:
  - if a doc names a file or command, that path or command must exist and be run before claiming the doc is current
- Evidence:
  - documented `cp documents/config.example.json` cannot succeed; file absent
- Confidence: High
- Last reviewed: 2026-04-08
- Promote to stronger rule? No

### LH-003: Generated references are worth seeding early — KIT
- Trigger:
  - kit-generated reference rebuilds
- Working heuristic:
  - not a product concern for this stdlib CLI unless CoreZero generated docs are the task
- Evidence:
  - original kit heuristic; no product generated-reference surface in `src/`
- Confidence: Low for this repo
- Last reviewed: 2026-04-08
- Promote to stronger rule? No

### LH-004: Agent tends to overscaffold when starting new files — ARCHIVED on 2026-06-25, see archive/deprecated-heuristics.md

### LH-005: Task validation evidence must be specific and machine-verifiable
- Trigger:
  - creating tasks in `tasks.md`
- Working heuristic:
  - every task must specify a concrete command or test file that runs and exits 0 as its validation proof, rather than vague human descriptions.
- Evidence:
  - tasks with vague proof criteria (e.g. "manual verify") lead to incomplete or skipped validation during alignment audits
- Confidence: High
- Last reviewed: 2026-06-23
- Promote to stronger rule? No

### LH-006: Token budget underestimation causes context compaction mid-complex task
- Trigger:
  - running a complex feature that loads many memory files and generates large tool output
- Working heuristic:
  - estimate token cost at feature start: count loaded files, add 2x buffer for tool output. If total exceeds 60% of capacity (120,000 tokens), split work into smaller phases and checkpoint between them.
- Evidence:
  - context compaction triggered mid-implementation, causing loss of design details and rework
- Confidence: High
- Last reviewed: 2026-06-18
- Promote to stronger rule? No — operational guidance, not normative

### LH-007: [PROMOTED CANDIDATE] Memory promotion thresholds trigger after files are already oversized
- Trigger:
  - running `/context-memory audit` or noticing a memory file exceeds 100 lines
- Working heuristic:
  - track memory file sizes proactively in feature extraction notes. When any file reaches the Early Warning threshold (per `core-policies.md` `## Memory Promotion Thresholds`), create a promotion proposal early rather than waiting for the Threshold Breach band.
- Evidence:
  - `project-knowledge-base.md` and `learned-heuristics.md` have grown past early-warning thresholds without triggering promotion because the check only runs during post-ship sync
- Confidence: Medium
- Last reviewed: 2026-06-18
- Promote to stronger rule? Yes — candidate for `core-zero/memories/repo/core-policies.md` Memory Promotion Thresholds

### LH-008: Domain packs are ignored when building new features — ARCHIVED on 2026-06-25, see archive/deprecated-heuristics.md

### LH-009: Blueprint is not the running system
- Trigger:
  - a request cites `documents/BUILDING_A_CODING_AGENT.md` as current architecture
- Working heuristic:
  - treat that file as a roadmap. Verify against `src/` + `tests/` + `documents/how-to-run.md` before planning work.
- Evidence:
  - blueprint lists slash commands, MCP, Pydantic, pytest, bootstrap_graph; none exist in `src/`
- Confidence: High
- Last reviewed: 2026-04-08
- Promote to stronger rule? No

### LH-010: Green unittest suite does not cover tool handlers
- Trigger:
  - changing `src/tools/handlers/*` or `src/tools/permissions.py`
- Working heuristic:
  - do not treat 18/18 `*_check.py` as proof of handler behavior. Add a focused check or state the gap.
- Evidence:
  - Phase A inventory: no tests for permissions, shell, file_io, network, execution, or other handlers
- Confidence: High
- Last reviewed: 2026-04-08
- Promote to stronger rule? No
