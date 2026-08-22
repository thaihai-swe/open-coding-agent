# Domain Packs

Each domain subdirectory under `core-zero/memories/domain/` is a self-contained domain pack with 4 required files (plus an optional `spec.md`).

| File               | When to load                                       | Purpose                                             |
| ------------------ | -------------------------------------------------- | --------------------------------------------------- |
| `glossary.md`      | 1+ trigger keywords match                          | Ubiquitous language — terms, definitions, examples  |
| `patterns.md`      | Planning or implementing in this domain            | Proven implementation patterns                      |
| `anti-patterns.md` | Code review, verification, debugging               | Known failure modes to avoid                        |
| `boundaries.md`    | Cross-domain calls, schema migrations, integration | What the domain owns, its contracts, and invariants |

## Directory schema

```
core-zero/memories/domain/
  <name>/
    glossary.md       — frontmatter with `domain:` and `triggers:` arrays
    patterns.md       — reusable implementation patterns
    anti-patterns.md  — failure modes to prevent
    boundaries.md     — ownership, contracts, invariants
    spec.md (optional) — canonical REQ/AC contract
```

When `context-load` or `session-start` receives an `--intent`, CoreZero matches its keywords against `triggers:` in each nested pack's `glossary.md` frontmatter to decide which packs to load. `core-zero/MASTER_INDEX.md` documents routing but does not select packs.

## File Schema

### glossary.md

Frontmatter:
```yaml
domain: <name>
triggers: [keyword1, keyword2, keyword3, keyword4, keyword5]
```
Body: Ubiquitous language table — terms the agent must use consistently when working in this domain. One row per term.

### patterns.md

Proven implementation patterns for this domain. Each pattern entry:
- Pattern name (bold heading)
- When to use it
- Key implementation notes
- Citation (file or PR where this was established)

### anti-patterns.md

Known failure modes and what NOT to do. Each entry:
- Anti-pattern name (bold heading)
- Why it fails in this domain
- What to do instead
- Citation (incident, review, or post-mortem)

### boundaries.md

What this domain owns, what it explicitly does NOT own, and how it integrates with adjacent domains.
- Owns: What this domain is responsible for
- Does not own: What this domain defers to other domains
- Integration contracts: How this domain's outputs become other domains' inputs

### spec.md (optional)

Canonical REQ/AC contract for the domain — the durable list of behaviors that all features in this domain must respect. Same shape as a feature `spec.md`.

Use it when:
- Multiple features touch the same set of REQs (auth, billing, data model).
- Cross-feature regressions are a real risk.
- Brownfield refactors need a stable map of "what already exists."

Skip it when:
- The domain has no shared contract — only ad-hoc utilities.
- The codebase is small enough that the source-of-truth can stay in code.

## Creating a Domain Pack

1. Create directory: `core-zero/memories/domain/<name>`
2. Create all 4 required files using the schema above.
3. Optionally create `spec.md` if the domain has a cross-cutting REQ/AC contract.
4. Add trigger keywords to `glossary.md` frontmatter.
5. Use `context-load` or `session-start` with an `--intent` containing one of the pack's trigger keywords to load the pack.

## Lifecycle

- Domain packs are adopter-owned — the kit seeds the schema but does not prescribe content.
- Update packs during `/context-memory` Post-Ship Sync when new patterns emerge from features.
- Promote durable patterns from `artifacts/features/<slug>/session-extracts.md` into the domain pack.
- Remove outdated entries when the codebase no longer uses a pattern.
- When a feature changes a domain's behavior or boundaries, edit `boundaries.md` to update its `## Invariants` and append a row to the `## Change Log`. This happens in the `/context-memory` post-ship sync.

## Shipped example

The kit currently keeps its worked schema demo as a legacy flat pack directly in
`core-zero/memories/domain/`. CoreZero discovers this form for backward
compatibility, but new domain packs should use the nested `<name>/` schema above.
Replace the example with a real named pack when the repository has stable domain
language.
