# Domain — Boundaries

> Ownership: Collaborative — skill-updated + user-maintained.
> Updated by: `/context-memory` post-ship sync when a feature changes domain ownership, an integration contract evolves, or an invariant is added/removed.
> Read by: `/spec-requirements`, `/spec-plan`, `/spec-implement`, `/harness-verify` to prevent boundary violations and regression.

Defines what this domain owns, does not own, how it integrates with adjacent domains, and the invariants that must never be violated. Replace with your domain's actual boundaries.

## Owns

- The core business entities and their lifecycle rules
- State transition logic and validation
- Domain events emitted when state changes
- The domain interface contracts (ports)

## Does Not Own

- Persistence mechanics (SQL queries, ORM mappings) — owned by Infrastructure
- HTTP request/response shaping — owned by API/Transport layer
- Authentication and session management — owned by Auth domain
- Notification delivery (email, SMS, push) — owned by Notification domain

## Integration Contracts

| Produces | Consumed By | Contract |
|-|-|-|
| Domain events | Event bus | Immutable event schema, versioned |
| Domain objects | Application services | Via repository port interface |

## Invariants

Rules that must never be violated when working in this domain. The agent must check these before implementing any change that touches this domain.

| ID | Invariant | Rationale |
|-|-|-|
| INV-001 | (Replace with a concrete rule — e.g., "An Order cannot transition from `Cancelled` to any other state.") | (Why this matters) |

*Add INV-002, INV-003, … as invariants are discovered. Never renumber or remove an ID — mark retired ones `Retired in <feature-slug> on <date>`.*

## Change Rules

- Domain interfaces are stable contracts. Changes require an ADR.
- Domain events are append-only. New fields may be added; existing fields must not be removed.
- Cross-domain calls go through declared integration contracts only — never direct imports.
- Any change to `## Invariants` must be reflected in the `## Change Log` below.

## Change Log

*Append one row per merged feature that modifies this file. Most recent first.*

| Date | Feature Slug | Change Summary |
|-|-|-|
| YYYY-MM-DD | example-feature | Initial scaffold |
