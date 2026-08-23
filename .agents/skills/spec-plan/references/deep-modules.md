# Deep Modules

Vocabulary for modules that hide complexity behind a small public interface. Use in `plan.md` module maps. Do not replace architecture language (`boundary`, `component`) in `architecture.md`. **Seam** = testable interface location.

## Glossary

**Module**: anything with an interface and an implementation (function, class, package, or slice).

**Interface**: everything a caller must know: types, invariants, ordering, errors, config, performance. Broader than a language `interface`.

**Implementation**: the module body. Use **adapter** when the seam is the topic.

**Depth**: leverage at the interface. **Deep** = lots of behavior behind a small interface. **Shallow** = interface nearly as complex as the implementation. Not a line-count ratio.

**Seam**: where the interface lives; behavior can be observed or substituted without editing the implementation.

**Adapter**: a concrete thing that satisfies an interface at a seam.

**Leverage**: capability per unit of interface callers learn.

**Locality**: change, bugs, knowledge, and verification concentrate in one place.

## Deletion test

Imagine deleting the module.

- Keep it when complexity reappears across N callers.
- Collapse it when complexity vanishes or moves to one caller.
- Concentrated complexity is the signal that deepening is worth proposing.

## Principles

- Depth is a property of the interface, not the implementation.
- The interface is the test surface. If a test must reach past it, the module is the wrong shape.
- One adapter = hypothetical seam. Two adapters = a real one. Do not invent seams unless something varies.
- Prefer existing seams. Fewer public seams is better.

## Design-it-twice

For Complex features, and Moderate features with two viable interface shapes:

1. Sketch two alternative interfaces.
2. Compare depth, seam placement, blast radius, and test surface.
3. Record the chosen option in `## Approach` and the rejected option in `## Complexity Tracking` or `## Alternatives Considered`.
4. If the trade-off is material and hard to reverse, invoke `/spec-adr`. Design-it-twice is not an ADR.

Do not invent speculative seams "for testability" when the public interface can carry the proof.
