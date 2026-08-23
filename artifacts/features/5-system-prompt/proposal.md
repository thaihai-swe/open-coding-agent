# Feature Proposal: 5-system-prompt

## Metadata
- Feature slug: `5-system-prompt`
- Profile: `Complex`
- Date / owner: 2026-08-22 / adopter
- Requested artifact name: `5.system-prompt` (harness slug `5-system-prompt`)
- References: Session 10 in `documents/BUILDING_A_CODING_AGENT.md`; https://learn.shareai.run/en/s10/

## Problem & Outcome
- Problem statement: The system prompt currently consists of a hardcoded combination of the Feature 3 planning instructions and the Feature 4 dynamic skills catalog. It lacks agent identity, workspace context (cwd), security policy awareness (workspace boundaries, hard denies, protected paths/keys, permission gates), active tools listing, and workspace-level instruction files (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`). As a result, the model is not grounded in the current repository environment, cannot follow local repo conventions, and lacks explicit security guardrails in prompt context. Furthermore, monolithic prompt construction makes it difficult to maintain and extend prompt capabilities without breaking existing features.
- Desired observable outcome:
  1. The system message is dynamically assembled from independent, topic-keyed prompt sections:
     - **Identity**: Role and working style ("You are a coding agent. Act, don't explain.").
     - **Workspace**: Current working directory path (`Working directory: <cwd>`).
     - **Planning**: The Feature 3 planning string ("You should plan before executing. Tools: create_task, list_tasks, get_task, claim_task, complete_task, cancel_task.").
     - **Security**: Hard deny commands, workspace bounds, protected paths/keys, and interactive permission gate policies.
     - **Tools**: List of currently registered tools formatted as `- <name>: <description>`.
     - **Skills**: The Feature 4 skill catalog (`Skills available:\n- **<name>**: <description>...\nUse load_skill to get full details when needed.` or `Skills available:\n(no skills found)`).
     - **Instructions (on-demand)**: Discovered instruction files from the project working directory (`AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md`), capped at 4,000 characters per file and 12,000 characters total, with content-hash deduplication. If no instruction files exist, this section is omitted.
  2. On every provider `complete()`, `QueryEngine` dynamically requests the assembled system prompt.
  3. The assembled system prompt is never persisted in `.cda/.sessions/<id>.json` transcripts.
  4. Changes to instruction files or skills mid-session take effect on the very next `complete()` call without restarting the CLI process.
- Non-goals:
  - Session 09 persistent memory (`MEMORY.md` / `.memory/`).
  - Walking up parent directories or scanning `~/.` for instruction files (only project cwd is scanned for instructions).
  - Injecting full JSON schemas into the prompt's `Tools` section (schemas continue to be passed in the provider API `tools` parameter).
  - Dumping dynamic project rules from `.cda/.permission_rules/rules.json` into the prompt.
  - Mode-specific prompts (Simple / Proactive / KAIROS / Coordinator).
  - Third-party template engines (e.g. Jinja2) or YAML parsers (pure stdlib Python 3.11+).

## Proposed Approach
- High-level architecture / public seams:
  - `src/prompt/assembler.py` (or `src/tools/prompt.py` / `src/application/prompt.py`):
    - `discover_instructions(cwd: Path | None = None) -> list[tuple[str, str]]`: Discovers `AGENTS.md`, `CLAUDE.md`, `CLAUDE.local.md` in cwd, truncates per-file (4,000 chars) and total (12,000 chars), and dedups duplicate content by SHA-256 hash.
    - `format_tools_section(tools: list[Tool] | None = None) -> str`: Formats registered tools list.
    - `format_security_section() -> str`: Formats the security and permission policies.
    - `assemble_system_prompt(...) -> str`: Assembles all sections separated by double newlines (`\n\n`).
  - `src/application/query_engine.py`:
    - Updates `QueryEngine._with_system` to call `assemble_system_prompt()` instead of `skills.build_system_message()`.
  - `src/tools/skills.py`:
    - Keeps `scan_skills`, `format_catalog`, `load_skill_content`, `expand_slash_prompt` intact. `build_system_message` is deprecated / delegated to the prompt assembler.
- Alternatives rejected and why (Design-it-Twice comparison):
  - *Alternative A: Static prompt assembly at session startup.*
    Rejected because it prevents the agent from detecting newly created or edited `AGENTS.md`, `CLAUDE.md`, or skill definitions mid-session.
  - *Alternative B: Injecting full JSON schemas in the prompt string.*
    Rejected because JSON schemas are already transmitted via the OpenAI-compatible `tools` API payload, and duplicating full schemas in the text prompt doubles token usage.
  - *Alternative C: Scanning instruction files up parent directories to filesystem root.*
    Rejected to enforce strict workspace boundaries and avoid accidental leakage of parent environment configurations or developer dotfiles.
- Preserved behavior:
  - Feature 1: Workspace bound, concurrent batch dispatch, shell/file/search/network handlers.
  - Feature 2: Permission gate, hard deny list, project rules in `.cda/.permission_rules/rules.json`, authorize prompt for MEDIUM/HIGH tools.
  - Feature 3: Task planning tools (`create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task`, `cancel_task`), per-session board, 3-round planning nag, messages-only session JSON.
  - Feature 4: Two-level skill loading (`load_skill` LOW Agent tool), skill catalog format, REPL slash command routing (`/<skill-name>`).

## Risks & Dependencies
- Component dependencies: `src/tools/registry.py`, `src/tools/skills.py`, `src/tools/task_board.py`, `src/tools/types.py`, `src/application/query_engine.py`.
- Security or migration risks: Instruction file truncation prevents prompt injection/token exhaustion attacks. Truncated files include a clear `[TRUNCATED]` indicator.
- Open questions (blocking only): None.

## Disposition
- Approval decision: `Approved`
- Next skill/action: `/spec-requirements` spec authoring -> `/spec-plan`
