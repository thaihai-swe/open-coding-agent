# ADR Log

## Index

- Write Contract — only spec-adr has write authority; immutable past entries
- Entry Template — ADR-NNN block format with date, slug, status, reversibility, superseded-by, summary
- Log — append-only list of ADR entries (Proposed/Accepted/Deprecated/Superseded)

Append-only index of Architecture Decision Records for this repository.

## Write Contract

- Write Authority: Only `/spec-adr` has write authority over this index.
- Trigger: Append a new entry immediately when a new ADR is proposed or accepted. Do not wait for feature merge.
- Immutability: Past log entries are immutable. If a decision changes, create a new ADR, update its status to `Superseded`, and reference the new ADR ID.
- Format: All log entries must follow the exact structure defined in the `## Entry Template` section below.
- Spec/Plan linkage: Each ADR must include the feature slug and related spec/plan links per the ADR template.

## How To Use This File

- One entry per ADR. Do not edit past entries.
- Each entry links to the full ADR artifact under `core-zero/project/adr/[number]-[slug].md`.
- Status values: `Proposed`, `Accepted`, `Deprecated`, `Superseded`.
- `/context-memory` may read this file for architecture drift detection but does not append entries.

## Entry Template

```
### ADR-<NNN> — <Short Decision Title>

- Date: YYYY-MM-DD
- Feature slug: <slug>
- Artifact: core-zero/project/adr/[number]-[slug].md
- Status: Proposed | Accepted | Deprecated | Superseded
- Reversibility: Easy | Moderate | Hard
- Superseded by: <ADR-NNN or none>
- One-line summary: <What was decided and why>
```

## Log

### ADR-001 — Example Decision

- Date: 2026-06-23
- Feature slug: kit-bootstrap
- Artifact: core-zero/project/adr/0001-example.md
- Status: Accepted
- Reversibility: Easy
- Superseded by: none
- One-line summary: Establish the ADR format and workflow for the kit.

<!-- Append new entries below in sequential ADR-NNN order. -->
