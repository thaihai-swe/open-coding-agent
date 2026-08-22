# Example Domain — Patterns

> Ownership: Collaborative — skill-updated + user-maintained.
> Updated by: `/context-memory` post-ship sync when a new reusable pattern is confirmed by a completed feature.
> Read by: `/spec-plan`, `/spec-implement` to reuse proven approaches and avoid reinvention.

Proven implementation patterns for this domain. Replace with your domain's actual patterns.

## Repository Pattern

When to use: Whenever domain objects need to be persisted or retrieved.

Key implementation notes:
- The repository interface is defined in the domain layer.
- Concrete implementations live in the infrastructure layer.
- The domain layer never imports from infrastructure.

Citation: Established in initial architecture design.

---

## Event-Driven State Transition

When to use: When domain state changes must be auditable and reversible.

Key implementation notes:
- Every state change emits a domain event.
- Events are immutable once emitted.
- Subscribers react to events; they do not mutate the originating aggregate.

Citation: Established in initial architecture design.
