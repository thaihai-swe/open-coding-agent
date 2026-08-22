## Template Pre-Fill Mode

The installer seeds 4 fillable documents under `core-zero/project/`, plus `core-zero/project/architecture.md` as a living doc. This skill pre-fills those seeded files so the user starts from evidence-based drafts instead of empty files. The goal is to reduce manual fill-in work, especially in brownfield repos where the answers already live in the code.

**Tier 1 — AI Pre-Fills From Code Evidence (user refines later):**

Read the repository and populate these from concrete evidence. Cite the source (file or config) where it adds confidence. Never invent values.

| Template | Pre-Fill From |
|-|-|
| `core-zero/project/tech-stack.md` | `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml`, lockfiles, import statements, framework config |
| `core-zero/project/architecture.md` | Top-level folder layout, module boundaries, entry points, build/CI config |
| `core-zero/project/project-constraints.md` | CI/CD settings, runtime version pins, resource limits, declared compliance tooling |

**Tier 2 — AI Asks Clarifying Questions (user-owned context):**

These need product, business, or policy context that is not reliably inferable from code. Ask 2-4 focused questions per template, then fill what the user answers. Leave unanswered sections as `[USER REVIEW NEEDED]`.

| Template | Ask About |
|-|-|
| `core-zero/project/product-sense.md` | Who the users are, the core problem, success metrics |
| `core-zero/project/glossary.md` | Domain terms with ambiguous or overloaded meaning |

**Pre-Fill Rules:**

- **Operate only on seeded files:** If a target doc is missing, stop and repair the install surface. Do not create ad-hoc replacements during init.
- **Brownfield:** Pre-fill Tier 1 aggressively from code. The repository is the system of record.
- **Greenfield:** Tier 1 evidence is thin. Fill what config exists, mark the rest `[USER REVIEW NEEDED]`.
- **Fact vs decision:** Stack, entrypoints, CI commands, and folder layout are facts. Product vision, SLOs, compliance, and gate confirmation are decisions.
- **Frontier questions:** Ask remaining Tier 2 decisions in one numbered batch with a recommended default. Do not serialize unblocked questions.
- **No fabrication:** If a value is not in the code and the user has not stated it, mark it `[UNKNOWN]` or `[USER REVIEW NEEDED]`. Do not guess product vision, SLOs, or compliance requirements.
- **Idempotent:** If a template already has user content (not the original template body), do not overwrite it. Append observations under a clearly marked section instead.
- **Report:** After pre-fill, list which templates were filled, which need user review, and where `[UNKNOWN]` or `[USER REVIEW NEEDED]` markers remain.
