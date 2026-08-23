## Template Pre-Fill Mode

Pre-fill seeded `corebase-specharness/project/` files from evidence so adopters start from drafts, not empty templates.

**Tier 1 — Pre-fill from code (user refines later):**

Cite the source. Never invent values.

| Template | Pre-Fill From |
|-|-|
| `tech-stack.md` | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, lockfiles, imports, framework config |
| `architecture.md` | Top-level layout, module boundaries, entry points, build/CI |
| `project-constraints.md` | CI/CD, runtime pins, resource limits, compliance tooling |

**Tier 2 — Ask clarifying questions:**

Ask 2–4 focused questions per template. Leave unanswered sections `[USER REVIEW NEEDED]`.

| Template | Ask About |
|-|-|
| `product-sense.md` | Users, core problem, success metrics |
| `glossary.md` | Domain terms with ambiguous meaning |

**Pre-Fill Rules:**

- Operate only on seeded files. If a target is missing, stop and repair the install surface.
- Brownfield: fill Tier 1 aggressively. The repo is the system of record.
- Greenfield: fill what config exists; mark the rest `[USER REVIEW NEEDED]`.
- Facts vs decisions: stack, entrypoints, CI, layout are facts. Vision, SLOs, compliance, gate confirmation are decisions.
- Ask remaining Tier 2 decisions in one numbered batch with a recommended default.
- If not in code and not stated, mark `[UNKNOWN]` or `[USER REVIEW NEEDED]`.
- Idempotent: do not overwrite user content. Append observations under a marked section.
- Report which templates were filled, which need review, and remaining `[UNKNOWN]` markers.
