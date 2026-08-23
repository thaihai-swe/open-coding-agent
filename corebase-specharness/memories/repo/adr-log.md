# Architecture Decision Log

Append-only index of Architecture Decision Records (ADRs) for this repository.

## Write Contract

- Write Authority: Only `/spec-adr` (or designated architect workflow) appends entries.
- Trigger: Append a new entry immediately when an ADR is proposed or accepted.
- Immutability: Past log entries are immutable. If a decision changes, create a new ADR, update the old entry to `Superseded`, and link the new ADR ID.
- Format: Follow the exact structure defined in `## Entry Template`.

## How To Use This File

- One entry per ADR. Do not edit past entries.
- Each entry links to the full ADR artifact under `corebase-specharness/project/adr/<number>-<slug>.md`.
- Status values: `Proposed`, `Accepted`, `Deprecated`, `Superseded`.
- `/context-memory` may read this file for architecture drift detection but does not append entries.

## Entry Template

```text
### ADR-<NNN> — <Short Decision Title>

- Date: YYYY-MM-DD
- Feature slug: <slug>
- Artifact: corebase-specharness/project/adr/<number>-<slug>.md
- Status: Proposed | Accepted | Deprecated | Superseded
- Reversibility: Easy | Moderate | Hard
- Superseded by: <ADR-NNN or none>
- One-line summary: <What was decided and why>
```

## Log

<!-- Append new entries below in sequential ADR-NNN order. -->
