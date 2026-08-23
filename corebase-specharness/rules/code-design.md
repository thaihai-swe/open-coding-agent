# Code-Design Principles

> Ownership: `Kit-managed`

Apply these rules with the same priority as `AGENTS.md` Section 0.

## Read before you write

- MUST inspect similar code before adding files; match local structure and style.
- SHOULD choose the smallest design that satisfies approved requirements.
- MUST keep fetching, domain logic, and presentation separated when they change independently.
- MUST use interfaces only for real boundaries or multiple implementations.
- MUST NOT create speculative wrappers, ports, injection slots, or deep inheritance.
- MUST preserve invariants behind validated APIs; do not expose mutable internal state.
- SHOULD compose behavior rather than inherit it.

## One Contract and One Resolution Path

- MUST use one spelling and representation per intent.
- MUST provide one canonical entry point for resolution, loading, and state changes.
- MUST move repeated caller setup into a shared helper.
- MUST centralize variant dispatch in one registry/resolver; avoid duplicated switches.
- MUST keep shared interfaces and implementations aligned; hide concrete-only behavior.

## Failures must reach a decision-maker

- MUST surface errors to a decision-maker; do not return silent empty results.
- MUST distinguish no result, unavailable dependency, and skipped work.
- MUST make required setup internal or fail explicitly when absent.
- MUST validate schemas, docs, config, examples, and code together on behavior changes.

## Abstraction Check & Deep Modules

- MUST apply deletion test: keep a module only if deleting it duplicates complexity across callers; collapse it if deletion only concentrates work in one caller.
- MUST design deep modules: maximize behavior behind small, simple public interfaces. Avoid shallow pass-through wrappers.
- MUST treat interface as test surface: callers and tests cross the same seam. Do not invent internal mock seams when the public interface is testable.
- MUST require two distinct adapters before committing to a permanent seam abstraction. One adapter represents a hypothetical seam.

## Clean Architecture & Layering

- **Dependency Direction:** Source dependencies MUST point inward toward core domain logic. Entities MUST NOT import persistence, HTTP frameworks, or UI libs.
- **Separation of Concerns:** MUST isolate business rules from persistence and transport. DB handles or HTTP objects MUST NOT pass into pure domain entities.
- **Ports & Adapters:** When domain needs external capabilities, MUST declare ports (interfaces) in domain; outer layers implement adapters.
- **No Anemic Models:** Domain entities MUST own their invariants, state transitions, and validation rules rather than acting as bare data holders.

## Domain-Driven Design (DDD)

- **Ubiquitous Language:** Code identifiers MUST strictly match `corebase-specharness/project/glossary.md` and domain packs. MUST NOT substitute generic technical synonyms for business terms.
- **Aggregate Roots:** MUST group coupled entities under a root entity. External callers MUST modify child state through methods on the root.
- **Value Objects:** SHOULD use immutable value objects for validated concepts (amounts, emails, ranges) instead of primitive types.
- **Bounded Contexts:** MUST NOT force a monolithic entity across divergent domains. Use separate models with explicit boundary mappings.

## Verify the path you claim to have fixed

- MUST run an end-to-end command exercising the changed path and verify side effects.
- MUST search for equivalent shapes when fixing a repeated defect class.
- MUST NOT claim success from compilation, mocks, or type checks alone when the real path is testable.
