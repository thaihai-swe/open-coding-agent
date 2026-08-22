# Kit Rules — How to Add a Rule

Rule files under `core-zero/rules/` are shipped overwrite-only files that define deterministic agent behavior constraints. Each file must:

1. **Use the `.md` extension** with a short kebab-case filename (e.g., `ponytail.md`, `security.md`).
2. **Start with a single `# Title` heading** that names the rule domain.
3. **Use `MUST` / `MUST NOT` / `SHOULD` language** per RFC 2119 conventions. Normative rule files (`code-design.md`, `security.md`, `architecture-principles.md`) MUST use this language. Style and behavior rule files (`caveman.md`, `ponytail.md`, `headroom.md`) MAY use imperative or conditional style when the MUST/MUST NOT form would be awkward.
4. **Be registered in `manifest.json`** under `files.overwrite` so it ships automatically.

To add a new rule:
1. Create `core-zero/rules/<name>.md` with title and rule content.
2. Add `core-zero/rules/<name>.md` to `manifest.json` `files.overwrite`.
3. Reference from the relevant SKILL.md `## Core Rules` section.
