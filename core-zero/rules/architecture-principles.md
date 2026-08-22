# Architecture Rules

> Normative rules for structural design, separation of concerns, and domain modeling.
> Load this file when making architectural choices, defining new entities, or structuring layers.

## Clean Architecture

- **Dependency Rule:** Source code dependencies MUST point inward, toward higher-level policies (domain). Inner circles (domain/entities) MUST NOT import or reference outer circles (DB, UI, frameworks, external APIs).
- **Separation of Concerns:** MUST keep business rules isolated from UI and database layers. MUST NOT pass infrastructure objects (database cursors, HTTP request/response objects, ORM sessions) into the domain layer.
- **Ports & Adapters:** When the domain needs to communicate with the outside world, MUST define interfaces (ports) in the domain layer. The outer (infrastructure) layer MUST implement these interfaces. MUST NOT let the domain layer depend on concrete infrastructure implementations.
- **Layering Violations:** MUST NOT import a specific DB driver, ORM, or framework from within the domain layer. If the domain needs persistence, it defines a port interface and the infrastructure layer provides the adapter.
- **Anemic Domain Model:** MUST NOT create domain entities as pure getters/setters with all behavior in services. Entities MUST own their invariants, state transitions, and business rules. Services complement entities — they do not replace their behavior.

## Domain-Driven Design (DDD)

- **Ubiquitous Language:** MUST use the exact terminology from `core-zero/project/glossary.md` in code identifiers (classes, variables, methods, tables). MUST NOT translate domain terms into generic technical synonyms (e.g., "Order" → "Record", "Invoice" → "Document").
- **Aggregate Root:** MUST group related entities into an aggregate with a single root entity. All modifications to aggregate children MUST go through the aggregate root to enforce invariants. MUST NOT allow direct modification of child entities bypassing the root.
- **Value Objects:** SHOULD prefer immutable value objects (e.g., `Money(amount, currency)`) over primitives when the primitive has business meaning or validation rules. MUST NOT use plain strings or ints for structured concepts that have invariants (primitive obsession).
- **Domain Services:** SHOULD use domain services for operations that do not naturally belong to a single entity or value object, but still encapsulate business rules. MUST NOT put domain logic in application services, controllers, or UI handlers when it belongs on a domain entity.
- **Bounded Contexts:** MUST NOT share a single domain model across contexts with different definitions of the same term. When contexts diverge, MUST define separate models with explicit translation maps at integration points.

## Deep Modules and Test Seams

Apply these rules with `code-design.md` and `skills/spec-plan/references/deep-modules.md`. A **seam** is the testable public interface location; it is not a DDD bounded context.

- MUST hide maximum behavior behind a small public interface (leverage for callers, locality for maintainers).
- MUST treat the public interface as the test surface. Callers and tests cross the same seam.
- MUST NOT introduce a permanent seam until two distinct adapters exist. One adapter is a hypothetical seam.
- MUST apply the deletion test before retaining a new module or wrapper.
