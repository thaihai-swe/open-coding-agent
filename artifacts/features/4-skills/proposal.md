# Feature Proposal: 4-skills

## Metadata
- Feature slug: `4-skills`
- Profile: `Complex`
- Date / owner: 2026-08-22 / adopter

## Problem & Outcome
- Problem statement: The coding agent CLI currently has a stub `skill` tool that only responds to `"known"`. It cannot load real domain workflows, design instructions, or project-specific coding guides dynamically into context. Stuffing all instructions into the system prompt wastes context window tokens on every turn. The agent needs a two-level knowledge loading system: a lightweight catalog in the system prompt on every turn, and a LOW-risk `load_skill(name: str)` tool that fetches full `SKILL.md` content on demand. Furthermore, the interactive REPL needs support for direct human slash command invocation (`/<skill-name>`).
- Desired observable outcome:
  1. The system prompt dynamically catalogs all skills discovered in process cwd `.agents/skills/` and global `~/.agents/skills/` (with project skills taking precedence).
  2. The model calls `load_skill(name="...")` to load the full `SKILL.md` content via `tool_result`.
  3. The interactive REPL allows users to invoke `/<skill-name>` to load that skill into the session context.
  4. Old stub `skill` tool is unregistered in favor of `load_skill(name)`.
  5. System prompt cleanly merges the Feature 3 planning instructions with the dynamic skill catalog on every provider completion, without polluting persisted session transcripts.
- Non-goals:
  - Third-party YAML parsing dependencies in `src/` (must use pure stdlib parser).
  - Subagent context isolation or forked execution (`context: fork`) from Session 06.
  - Automatic recursive bundling/injection of referenced files in `references/`, `scripts/`, or `assets/` (the model accesses them on demand using existing `read_file` or `bash` tools).
  - Modifying the Feature 2 permission gate or `.cda/` session transcript storage format.

## Proposed Approach
- High-level architecture / public seams:
  - `src/tools/skills.py` (or `src/domain/skills.py` / `src/infrastructure/skills.py`): Discover and parse `SKILL.md` files from project `.agents/skills/` and `~/.agents/skills/`. Extract frontmatter fields (`name`, `description`, `when_to_use`) using a robust stdlib parser.
  - `src/tools/handlers/agent.py`: Replace stub `skill` with `load_skill(name: str)` tool handler (category: Agent, risk: LOW) that queries the skill registry.
  - `src/application/query_engine.py`: Build dynamic system message on each provider `complete()` combining planning instructions + formatted skill catalog (`Skills available:\n- **<name>**: <description>...`).
  - `src/presentation/cli.py` & `src/presentation/terminal_ui.py`: Detect `/<skill-name>` in the REPL input loop and dispatch skill loading/execution.
- Alternatives rejected and why (Design-it-Twice comparison):
  - *Alternative A: Static skill scanning at startup only.* Rejected in favor of turn/complete scanning so newly created or edited `SKILL.md` files take immediate effect without restarting the CLI.
  - *Alternative B: External PyYAML dependency.* Rejected to maintain zero third-party dependencies in `src/` as required by project constraints.
  - *Alternative C: Path-based loading (passing file paths to the tool).* Rejected due to security/path traversal risks; name-based registry lookup ensures safe bounded access.
- Preserved behavior:
  - Feature 1: Workspace bound, concurrent tool execution, output rendering.
  - Feature 2: Permission gate, hard deny list, `.cda/` rules.
  - Feature 3: Task planning tools (`create_task`, `list_tasks`, etc.), 3-round planning nag, session message isolation.

## Risks & Dependencies
- Component dependencies: `src/tools/registry.py`, `src/application/query_engine.py`, `src/presentation/cli.py`.
- Security or migration risks: Path traversal is mitigated by name-indexed registry lookup. Colliding skill names are deterministically resolved by project precedence.
- Open questions (blocking only): None.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-requirements` spec authoring -> `/spec-plan`
