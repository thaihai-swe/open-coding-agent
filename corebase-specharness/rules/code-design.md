# Code-Design Principles

> Ownership: `Kit-managed`

Apply these rules with the same priority as `AGENTS.md` Section 0.

## Read before you write

- MUST inspect similar code before adding files or modules; match local structure.
- SHOULD choose the smallest design that satisfies approved requirements.
- MUST keep fetching, domain logic, and presentation separated when they change independently.
- MUST use interfaces only for real architectural boundaries or multiple implementations.
- MUST NOT create speculative wrappers, ports, injection slots, or deep inheritance.
- MUST preserve invariants behind validated APIs; do not expose mutable internal state.
- SHOULD compose behavior rather than inherit it.

## One Contract and One Resolution Path

- MUST use one spelling and one representation for each intent.
- MUST provide one canonical entry point for resolution, loading, and state changes.
- MUST move repeated caller setup into a shared helper.
- MUST centralize variant dispatch in one registry/resolver; do not duplicate switches.
- MUST keep shared interfaces and implementations aligned; hide concrete-only behavior.

## Failures must reach a decision-maker

- MUST surface errors to a decision-maker; do not silently return empty data after failure.
- MUST distinguish no result, unavailable dependency, and skipped work.
- MUST make required setup internal to the operation or fail explicitly when absent.
- MUST validate schemas, docs, configuration, examples, and code together whenever behavior changes.

## Abstraction Check & Deep Modules

Before retaining or creating a layer, apply the deletion test and depth criteria:

- MUST apply the deletion test: keep a module when deleting it duplicates meaningful complexity across callers; collapse it when deletion only renames or concentrates work in one caller.
- MUST design deep modules: place maximum behavior behind a small, simple public interface (leverage for callers, locality for maintainers). Avoid shallow pass-through wrappers where the interface is nearly as complex as the implementation.
- MUST treat the interface as the test surface: callers and tests cross the same seam. Do not introduce hypothetical seams or internal mock seams when tests can observe behavior through the public interface.
- MUST require two distinct adapters before committing to a permanent seam abstraction. One adapter represents a hypothetical seam.

## Clean Architecture & Layering

- **Dependency Direction:** Source code dependencies MUST point inward toward core business domain logic. Inner circles (entities/domain rules) MUST NOT import or reference outer circles (database drivers, HTTP frameworks, third-party UI libraries).
- **Separation of Concerns:** MUST isolate business rules from persistence and transport mechanisms. Infrastructure objects (DB connections, HTTP request/response payloads, ORM handles) MUST NOT pass into pure domain entities.
- **Ports & Adapters:** When the domain needs external capabilities (storage, external APIs, notifications), MUST declare boundary interfaces (ports) in the domain layer. Outer layers provide concrete implementations (adapters).
- **No Anemic Domain Models:** Entities and domain objects MUST own their internal invariants, state transitions, and validation rules rather than acting as bare data holders with logic scattered across procedural scripts.

## Domain-Driven Design (DDD)

- **Ubiquitous Language:** Code identifiers (classes, functions, database columns) MUST strictly match domain definitions from `corebase-specharness/project/glossary.md` and domain packs. MUST NOT substitute generic technical synonyms for business terms.
- **Aggregate Roots:** MUST group tightly coupled entities into aggregates with one designated root entity. External callers MUST modify child state through methods on the aggregate root to enforce consistency boundaries.
- **Value Objects:** SHOULD use immutable value objects for structured concepts with validation rules (e.g. monetary amounts, email addresses, date ranges) rather than plain primitive types (preventing primitive obsession).
- **Bounded Contexts:** MUST NOT force a single monolithic entity model across divergent functional areas with differing vocabularies. When business definitions differ, maintain separate models with explicit boundary mappings.

## Verify the path you claim to have fixed

- MUST run an end-to-end command that exercises the changed path and inspect its side effect.
- MUST search for equivalent shapes when fixing a repeated defect class.
- MUST NOT claim success from compilation, mocks, or type checks alone when the real path is testable.
