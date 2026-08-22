# Feature Artifacts

Each feature gets a subdirectory under `artifacts/features/<slug>/`. Below are all standard artifacts, their tier, location, owning skill, phase of creation, and schema reference.

| Artifact | Tier | Location | Owning skill | Phase | Schema |
|-|-|-|-|-|-|
| `status.md` | Durable | `artifacts/features/<slug>/` | spec-research / all | All | `_shared/status-template.md` |
| `analysis.md` | Durable | `artifacts/features/<slug>/` | spec-research | Spec | `spec-research/references/analysis-template.md` |
| `proposal.md` | Durable | `artifacts/features/<slug>/` | spec-requirements | Spec | `spec-requirements/references/proposal-template.md` |
| `spec.md` | Durable | `artifacts/features/<slug>/` | spec-requirements | Spec | `spec-requirements/references/spec-template.md` |
| `plan.md` | Durable | `artifacts/features/<slug>/` | spec-plan | Plan | `spec-plan/references/plan-template.md` |
| `tasks.md` | Durable | `artifacts/features/<slug>/` | spec-tasks | Plan | `spec-tasks/references/tasks-template.md` |
| `session.md` | Ephemeral | `.corezero/sessions/<slug>/` | spec-implement / `python3 core-zero/scripts/core/cli.py session-*` | Implement | `scripts/core/cli.py` |
| `session-extracts.md` | Semi-durable | `artifacts/features/<slug>/` | spec-implement / `python3 core-zero/scripts/core/cli.py session-end` | Implement | `scripts/core/cli.py` |
| `requirements-review.md` | Semi-durable | `artifacts/features/<slug>/` | spec-requirements | Spec | `spec-requirements/references/requirements-review-template.md` |
| `testing-scenarios.md` | Durable | `artifacts/features/<slug>/` | spec-testing-scenario (optional) | Verify | `spec-testing-scenario/references/testing-scenarios-template.md` |
| `review.md` | Durable | `artifacts/features/<slug>/` | harness-verify | Verify | `harness-verify/references/review-template.md` |

Complexity Notes:
- `proposal.md` — generated for Moderate/Complex only.


## Delivery Profiles (Complexity Tiers)

Features use one of three delivery profiles to control which artifacts are required:

| Profile | Required Artifacts | Use Case |
|---------|------------------|----------|
| **Simple** | `status.md`, `spec.md`, compact `plan.md`, compact `tasks.md` | 1 AC, 1-2 files changed; trivial bugfix or one-line change |
| **Moderate** | `status.md`, `spec.md`, `plan.md`, `tasks.md` (current default) | Standard feature requiring design and task breakdown |
| **Complex** | Same as Moderate + optional research, proposal, ADR, and reviews | Multi-component feature with uncertainty or novel design |

### Compact Artifacts (Simple Profile)

Simple features use compact `spec.md`, `plan.md`, and `tasks.md` forms while preserving the same lifecycle and traceability path:

```markdown
# Compact Feature Specification

## Metadata

- Delivery profile: Simple
- Status: Draft

## Problem Statement

[Brief description of the issue or change]

## Acceptance Criteria

### AC-001: [brief expected outcome]

- Expected result: [observable outcome]

## Expected Changes

- [ ] [path or component]

## Validation Evidence

- [ ] Command: [exact command]
- [ ] Result: [output or observation]

## Completion Checklist

- [ ] Implementation complete
- [ ] Validation passed
```

`plan.md` records Metadata, Lightweight Design, and the applicable Delivery fields. `tasks.md` records one compact milestone with a canonical `T-NNN` task entry, AC coverage, proof, and evidence.

### Artifact Existence Summary

The table below shows which artifacts are mandatory per profile.

## Lifecycle

- Ephemeral session state (`session.md`) is managed by `python3 core-zero/scripts/core/cli.py session-*` commands.
- Durable files are never auto-deleted. They remain as historical record.
- Semi-durable files (`session-extracts.md`, `requirements-review.md`) are retained until manually cleaned or triaged.
