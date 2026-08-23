# Deep Modules

Shared vocabulary for designing modules that hide complexity behind a small public interface. Use these terms in `plan.md` module maps and in architectural surveys. Do not replace CoreBase SpecHarness architecture language (`boundary`, `component`) in `architecture.md`; treat **seam** as the testable interface location.

## Glossary

Use these terms exactly when the subject is module shape or testability.

**Module**: anything with an interface and an implementation. Scale-agnostic: a function, class, package, or tier-spanning slice.

**Interface**: everything a caller must know to use the module correctly: type surface, invariants, ordering constraints, error modes, required configuration, and performance characteristics. Broader than a language `interface` keyword.

**Implementation**: the body of the module. Distinct from **adapter**: reach for "adapter" when the seam is the topic; "implementation" otherwise.

**Depth**: leverage at the interface. A module is **deep** when a large amount of behavior sits behind a small interface, **shallow** when the interface is nearly as complex as the implementation. Depth is not a ratio of implementation lines to interface lines.

**Seam**: the location at which a module's interface lives; a place where behavior can be observed or substituted without editing the implementation. Distinct from a DDD bounded context.

**Adapter**: a concrete thing that satisfies an interface at a seam. Describes role, not substance.

**Leverage**: what callers get from depth. More capability per unit of interface they learn.

**Locality**: what maintainers get from depth. Change, bugs, knowledge, and verification concentrate in one place rather than spreading across callers.

## Deletion test

Imagine deleting the module.

- Keep it when complexity reappears across N callers.
- Collapse it when complexity vanishes or merely moves to one caller.
- A "yes, concentrates complexity" result is the signal that a deepening is worth proposing.

## Principles

- Depth is a property of the interface, not the implementation. A deep module may have internal seams used by its own tests; those are not part of the public interface.
- The interface is the test surface. Callers and tests cross the same seam. If a test must reach past the interface, the module is probably the wrong shape.
- One adapter means a hypothetical seam. Two adapters means a real one. Do not introduce a seam unless something actually varies across it.
- Prefer existing seams to new ones. The fewer public seams in a change, the better.

## Design-it-twice

For Complex features, and for Moderate features where two interface shapes are both viable:

1. Sketch two alternative interfaces for the same responsibility.
2. Compare them on depth, seam placement, blast radius, and how tests would hit the interface.
3. Record the chosen option in `## Approach` and the rejected option in `## Complexity Tracking` or `## Alternatives Considered`.
4. If the trade-off is material and hard to reverse, invoke `/spec-adr`. Design-it-twice does not replace an ADR.

Do not invent speculative seams "for testability" when the public interface can carry the proof.
